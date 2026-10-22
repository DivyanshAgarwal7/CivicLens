"""Selenium smoke tests for the CivicLens single-page application.

Run against a disposable local environment:
    python -m pytest -v test_civiclens_selenium.py

The suite derives selectors from current visible labels and button text. It
provisions a unique Citizen through the development API and must never run
with production credentials or a production database.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_URL = os.getenv("CIVICLENS_BASE_URL", "http://localhost:5173").rstrip("/")
API_BASE_URL = os.getenv("CIVICLENS_API_BASE_URL", "http://127.0.0.1:8000/api").rstrip("/")
WAIT_SECONDS = int(os.getenv("SELENIUM_WAIT_SECONDS", "20"))
SCREENSHOT_DIR = Path(os.getenv("SELENIUM_SCREENSHOT_DIR", "selenium-artifacts"))


@dataclass(frozen=True)
class DisposableAccount:
    email: str
    password: str
    full_name: str


def _api_json(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


@pytest.fixture(scope="session")
def disposable_account() -> DisposableAccount:
    """Provision a unique local Citizen; never use a real account."""
    override_email = os.getenv("CIVICLENS_TEST_EMAIL")
    password = os.getenv("CIVICLENS_TEST_PASSWORD", "SeleniumCivic!2026Test")
    if override_email:
        return DisposableAccount(override_email, password, "CivicLens Selenium Citizen")

    account = DisposableAccount(
        f"selenium-{int(time.time())}-{os.getpid()}@example.com",
        password,
        "CivicLens Selenium Citizen",
    )
    try:
        _api_json(
            "/auth/register",
            {
                "email": account.email,
                "password": account.password,
                "password_confirmation": account.password,
                "full_name": account.full_name,
                "phone": "+919800000000",
            },
        )
    except urllib.error.HTTPError as exc:
        try:
            safe_body = json.loads(exc.read().decode("utf-8"))
            safe_detail = safe_body.get("detail", "validation error") if isinstance(safe_body, dict) else "validation error"
        except (ValueError, UnicodeDecodeError):
            safe_detail = "validation error"
        pytest.fail(f"Backend test-account provisioning unavailable: HTTP {exc.code}: {safe_detail}")
    except urllib.error.URLError as exc:
        pytest.fail(f"Backend test-account provisioning unavailable: {exc}")
    return account


@pytest.fixture
def driver(request):
    """Create a headless browser and capture screenshots for real failures."""
    browser = os.getenv("CIVICLENS_BROWSER", "chrome").lower()
    configured_binary = os.getenv("CIVICLENS_BROWSER_BINARY")
    candidates = {
        "chrome": [
            configured_binary,
            shutil.which("chrome"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        ],
        "edge": [
            configured_binary,
            shutil.which("msedge"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ],
        "firefox": [configured_binary, shutil.which("firefox")],
    }
    binary = next((candidate for candidate in candidates.get(browser, []) if candidate and Path(candidate).exists()), None)
    if not binary:
        pytest.fail(f"Selenium {browser} browser binary unavailable; set CIVICLENS_BROWSER_BINARY to a disposable browser executable")
    configured_driver = os.getenv("CIVICLENS_DRIVER_BINARY")
    driver_candidates = {
        "chrome": [configured_driver] if configured_driver else [shutil.which("chromedriver"), r"C:\WebDriver\chromedriver.exe"],
        "edge": [configured_driver] if configured_driver else [shutil.which("msedgedriver"), r"C:\WebDriver\msedgedriver.exe"],
        "firefox": [configured_driver] if configured_driver else [shutil.which("geckodriver"), r"C:\WebDriver\geckodriver.exe"],
    }
    driver_binary = next((candidate for candidate in driver_candidates.get(browser, []) if candidate and Path(candidate).exists()), None)
    if not driver_binary:
        pytest.fail(f"Selenium {browser} driver unavailable; set CIVICLENS_DRIVER_BINARY to a matching driver executable")
    try:
        if browser == "firefox":
            options = webdriver.FirefoxOptions()
            options.add_argument("-headless")
            options.binary_location = binary
            current = webdriver.Firefox(options=options, service=FirefoxService(executable_path=driver_binary))
        elif browser == "edge":
            options = webdriver.EdgeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.binary_location = binary
            current = webdriver.Edge(options=options, service=EdgeService(executable_path=driver_binary))
        else:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1440,1000")
            options.add_argument("--disable-notifications")
            options.add_argument("--no-sandbox")
            options.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})
            options.binary_location = binary
            current = webdriver.Chrome(options=options, service=ChromeService(executable_path=driver_binary))
    except WebDriverException as exc:
        pytest.fail(f"Selenium {browser} browser/driver unavailable: {exc.msg or exc}")

    current.implicitly_wait(0)
    # Each test gets a clean SPA authentication state. This does not touch backend data.
    current.get(BASE_URL)
    current.delete_all_cookies()
    current.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    yield current
    try:
        if getattr(request.node, "rep_call", None) and request.node.rep_call.failed:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            current.save_screenshot(str(SCREENSHOT_DIR / f"{request.node.name}.png"))
    finally:
        current.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
    if report.when == "call" and report.failed:
        current = item.funcargs.get("driver")
        if current is not None:
            print("\n--- CivicLens Selenium failure diagnostics ---")
            print(f"URL: {current.current_url}")
            print(f"Title: {current.title}")
            print(f"Headings: {[x.text.strip() for x in current.find_elements(By.CSS_SELECTOR, 'h1,h2,h3') if x.is_displayed()][:10]}")
            print(f"Alerts: {[x.text.strip() for x in current.find_elements(By.CSS_SELECTOR, '[role=alert]') if x.is_displayed()]}")
            print(f"Expected test IDs in DOM: {{name: current.find_elements(By.CSS_SELECTOR, f'[data-testid={{{{name}}}}]').__len__() for name in ['login-screen','login-error','register-screen','register-error']}}")
            print(f"Visible body text: {current.find_element(By.TAG_NAME, 'body').text[:1200]!r}")
            try:
                for entry in current.get_log("browser")[-10:]:
                    print(f"Browser console: {entry.get('level')} {entry.get('message', '')[:500]}")
            except Exception as exc:
                print(f"Browser console unavailable: {type(exc).__name__}")
            try:
                for entry in current.get_log("performance"):
                    message = json.loads(entry["message"]).get("message", {})
                    if message.get("method") == "Network.responseReceived":
                        response = message.get("params", {}).get("response", {})
                        url = response.get("url", "")
                        if "/api/auth/" in url:
                            print(f"Auth API response: {response.get('status')} {url.split('?')[0]}")
            except Exception as exc:
                print(f"Auth network diagnostics unavailable: {type(exc).__name__}")
            print("--- end diagnostics ---")


def _print_failure_diagnostics(driver):
    print("\n--- CivicLens Selenium failure diagnostics ---")
    print(f"URL: {driver.current_url}")
    print(f"Title: {driver.title}")
    print(f"Headings: {[x.text.strip() for x in driver.find_elements(By.CSS_SELECTOR, 'h1,h2,h3') if x.is_displayed()][:10]}")
    print(f"Alerts: {[x.text.strip() for x in driver.find_elements(By.CSS_SELECTOR, '[role=alert]') if x.is_displayed()]}")
    ids = {name: len(driver.find_elements(By.CSS_SELECTOR, f'[data-testid="{name}"]')) for name in ['login-screen', 'login-error', 'register-screen', 'register-error']}
    print(f"Expected test IDs in DOM: {ids}")
    try:
        print(f"Visible body text: {driver.find_element(By.TAG_NAME, 'body').text[:1200]!r}")
    except Exception:
        print("Visible body text: unavailable")
    try:
        for entry in driver.get_log("browser")[-10:]:
            print(f"Browser console: {entry.get('level')} {entry.get('message', '')[:500]}")
    except Exception as exc:
        print(f"Browser console unavailable: {type(exc).__name__}")
    try:
        for entry in driver.get_log("performance"):
            message = json.loads(entry["message"]).get("message", {})
            if message.get("method") == "Network.responseReceived":
                response = message.get("params", {}).get("response", {})
                url = response.get("url", "")
                if "/api/auth/" in url:
                    print(f"Auth API response: {response.get('status')} {url.split('?')[0]}")
    except Exception as exc:
        print(f"Auth network diagnostics unavailable: {type(exc).__name__}")
    print("--- end diagnostics ---")


def wait_visible(driver, locator, timeout=WAIT_SECONDS):
    try:
        return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))
    except TimeoutException:
        _print_failure_diagnostics(driver)
        raise


def wait_clickable(driver, locator, timeout=WAIT_SECONDS):
    try:
        return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
    except TimeoutException:
        _print_failure_diagnostics(driver)
        raise


def click_text(driver, text: str):
    element = wait_clickable(driver, (By.XPATH, f"//button[normalize-space()={json.dumps(text)}]"))
    element.click()
    return element


def submit_form(driver):
    """Submit the active form, avoiding duplicate navbar auth buttons."""
    wait_clickable(driver, (By.CSS_SELECTOR, 'form button[type="submit"]')).click()


def fill(driver, locator, value: str):
    element = wait_visible(driver, locator)
    element.clear()
    element.send_keys(value)
    return element


def label_control(label_text: str, tag: str = "input"):
    return (By.XPATH, f"//label[normalize-space()={json.dumps(label_text)}]/following::{tag}[1]")


def login(driver, account: DisposableAccount):
    driver.get(BASE_URL)
    fill(driver, (By.CSS_SELECTOR, 'input[name="email"]'), account.email)
    fill(driver, (By.CSS_SELECTOR, 'input[name="password"]'), account.password)
    submit_form(driver)
    try:
        WebDriverWait(driver, WAIT_SECONDS).until(
            lambda current: current.find_elements(By.XPATH, "//*[normalize-space()='Citizen Action Hub']")
            or current.find_elements(By.CSS_SELECTOR, '[data-testid="login-error"]')
        )
    except TimeoutException:
        _print_failure_diagnostics(driver)
        pytest.fail(f"Login did not reach a dashboard or render login-error; URL={driver.current_url}, title={driver.title}")
    error = driver.find_elements(By.CSS_SELECTOR, '[data-testid="login-error"]')
    if error and error[0].is_displayed():
        pytest.fail(f"Login API/UI rejected the disposable account: {error[0].text.strip() or 'empty login error'}")
    wait_visible(driver, (By.XPATH, "//*[normalize-space()='Citizen Action Hub']"))


def open_report_screen(driver):
    click_text(driver, "Report Issue")
    wait_visible(driver, (By.XPATH, "//*[normalize-space()='Report a Civic Problem']"))


def test_login_page_loads(driver):
    driver.get(BASE_URL)
    assert driver.current_url.startswith("http://localhost:5173"), (
        f"Unexpected frontend origin: {driver.current_url}; expected the local Vite app at http://localhost:5173"
    )
    assert driver.find_elements(By.CSS_SELECTOR, '[data-testid="login-screen"]'), (
        "The running frontend does not contain the current login-screen test ID. "
        f"URL={driver.current_url}; restart Vite from the current frontend source."
    )
    assert wait_visible(driver, (By.CSS_SELECTOR, 'input[name="email"]')).get_attribute("type") == "email"
    assert wait_visible(driver, (By.CSS_SELECTOR, 'input[name="password"]')).get_attribute("type") == "password"
    assert wait_visible(driver, (By.XPATH, "//button[normalize-space()='Sign In']")).is_displayed()


def test_invalid_login_is_rejected(driver):
    driver.get(BASE_URL)
    fill(driver, (By.CSS_SELECTOR, 'input[name="email"]'), "invalid-selenium@example.com")
    fill(driver, (By.CSS_SELECTOR, 'input[name="password"]'), "DefinitelyWrong!2026")
    submit_form(driver)
    error = wait_visible(driver, (By.CSS_SELECTOR, '[data-testid="login-error"]'))
    assert error.text.strip()
    assert wait_visible(driver, (By.CSS_SELECTOR, 'input[name="password"]')).is_displayed()
    assert "Citizen Action Hub" not in driver.page_source


def test_registration_rejects_weak_password(driver):
    driver.get(BASE_URL)
    click_text(driver, "Create Citizen Account")
    wait_visible(driver, (By.CSS_SELECTOR, '[data-testid="register-screen"]'))
    fill(driver, (By.CSS_SELECTOR, 'input[name="full_name"]'), "Selenium Validation Citizen")
    fill(driver, (By.CSS_SELECTOR, 'input[name="email"]'), f"weak-{int(time.time())}@example.com")
    # Long enough for native HTML validation, but missing uppercase and special characters.
    weak_password = "weakpassword1"
    fill(driver, (By.CSS_SELECTOR, '#register-password'), weak_password)
    fill(driver, (By.CSS_SELECTOR, '#register-password-confirmation'), weak_password)
    click_text(driver, "Complete Registration")
    error = wait_visible(driver, (By.CSS_SELECTOR, '[data-testid="register-error"]'))
    assert error.text.strip()


def test_valid_login_with_disposable_account(driver, disposable_account):
    login(driver, disposable_account)
    assert "Citizen Action Hub" in driver.page_source


def test_required_issue_fields_are_validated(driver, disposable_account):
    login(driver, disposable_account)
    open_report_screen(driver)
    title = wait_visible(driver, label_control("Report Title *"))
    description = wait_visible(driver, label_control("Detailed Description *", "textarea"))
    assert driver.execute_script("return arguments[0].checkValidity()", title) is False
    assert driver.execute_script("return arguments[0].checkValidity()", description) is False


def test_valid_citizen_issue_submission_and_detail(driver, disposable_account):
    login(driver, disposable_account)
    open_report_screen(driver)
    issue_title = f"Selenium issue {int(time.time())}"
    fill(driver, label_control("Report Title *"), issue_title)
    fill(driver, label_control("Detailed Description *", "textarea"), "Automated disposable test report for a pothole near the test landmark.")
    click_text(driver, "Submit Civic Issue")
    WebDriverWait(driver, 30).until(
        lambda current: current.find_elements(By.XPATH, "//*[normalize-space()='Transparent Audit Log & Status History']")
        or current.find_elements(By.XPATH, "//*[normalize-space()='Possible Duplicate Report Detected']")
    )
    separate_issue = driver.find_elements(By.XPATH, "//button[normalize-space()='Submit As Separate Issue']")
    if separate_issue:
        separate_issue[0].click()
    wait_visible(driver, (By.XPATH, "//*[normalize-space()='Transparent Audit Log & Status History']"), timeout=30)
    assert issue_title in driver.page_source


def test_created_issue_can_be_found_and_missing_image_uses_fallback(driver, disposable_account):
    login(driver, disposable_account)
    open_report_screen(driver)
    issue_title = f"Selenium fallback issue {int(time.time())}"
    fill(driver, label_control("Report Title *"), issue_title)
    fill(driver, label_control("Detailed Description *", "textarea"), "Automated disposable test report used to verify the missing-image fallback.")
    click_text(driver, "Submit Civic Issue")
    WebDriverWait(driver, 30).until(
        lambda current: current.find_elements(By.XPATH, "//*[normalize-space()='Transparent Audit Log & Status History']")
        or current.find_elements(By.XPATH, "//*[normalize-space()='Possible Duplicate Report Detected']")
    )
    separate_issue = driver.find_elements(By.XPATH, "//button[normalize-space()='Submit As Separate Issue']")
    if separate_issue:
        separate_issue[0].click()
    wait_visible(driver, (By.XPATH, "//*[normalize-space()='Transparent Audit Log & Status History']"), timeout=30)
    click_text(driver, "Back to Dashboard")
    wait_visible(driver, (By.XPATH, "//*[normalize-space()='Citizen Action Hub']"))
    wait_visible(driver, (By.XPATH, f"//*[normalize-space()={json.dumps(issue_title)}]"), timeout=30)
    fallback = driver.find_elements(By.XPATH, "//*[@role='img' and contains(@aria-label, 'No image available')]")
    assert fallback or "No issue image available" in driver.page_source


if __name__ == "__main__":
    raise SystemExit("Run with: python -m pytest -v test_civiclens_selenium.py")
