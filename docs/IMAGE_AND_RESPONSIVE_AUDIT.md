# CivicLens Phase 9 — Image and Responsive UI Audit

## Scope and evidence

The image path was traced from seed data and persisted issue records through the FastAPI serializers and React issue cards, detail views, engineer evidence workflow, and `/uploads` serving. The responsive review covered the main citizen, verification, detail, officer, engineer, admin, registration, login, modal, drawer, and upload surfaces by source inspection and production build validation.

## Root cause and correction

The incorrect-image behavior was an application data problem. `backend/seed_data.py` used unrelated Unsplash URLs for civic issues, a resolution record reused an unrelated stock image, and `EngineerPortalScreen` prefilled a hardcoded external image when marking work resolved. The frontend then rendered `image_urls[0]` without validating ownership or handling load failure. Existing JSON data also contains historical external URLs and empty image arrays; it was preserved as required.

The correction is deliberately additive and does not reset data:

- Seed data now starts with no image unless an actual upload is associated.
- `_public_issue` allow-lists only basename-only local `/uploads/<filename>` paths and sanitizes resolution evidence in the same way. External, traversal, query-string, and malformed paths are omitted.
- `IssueImage` validates the source again in the browser, provides a neutral accessible fallback, and changes to the fallback on load failure.
- Citizen, community verification, issue detail, resolution evidence, and engineer evidence preview all use the shared component.
- Resolution evidence must still be uploaded before a resolved transition; no placeholder is submitted as evidence.

## Responsive changes

- Added a compact mobile navigation menu for widths below the existing `md` breakpoint.
- Added mobile wrapping for lifecycle/status grids that previously forced four narrow columns.
- Added bounded, scrollable modal bodies for engineer, officer, duplicate-warning, and other long-content interactions.
- Existing responsive grid breakpoints and horizontal table scrolling were retained.

## Viewport matrix

| Viewport | Expected validation | Status |
|---|---|---|
| 320×568 | No horizontal page overflow; menu and modals usable; cards stack | NOT RUN — browser automation unavailable in this pass |
| 360×800 | Same, with upload and detail content readable | NOT RUN — browser automation unavailable in this pass |
| 390×844 | Same, lifecycle/status labels wrap | NOT RUN — browser automation unavailable in this pass |
| 768×1024 | Tablet navigation and two-column surfaces remain usable | NOT RUN — browser automation unavailable in this pass |
| 1024×768 | Desktop navigation and operational tables fit/scroll intentionally | NOT RUN — browser automation unavailable in this pass |
| 1366×768 | Primary desktop layout and modal bounds | NOT RUN — browser automation unavailable in this pass |
| 1920×1080 | Wide layout remains centered and does not stretch content excessively | NOT RUN — browser automation unavailable in this pass |

The frontend TypeScript production build passed, which validates the compiled responsive changes but does not replace real browser viewport inspection. Manual verification should open the app at each matrix size and check the browser horizontal scrollbar, mobile menu, issue-card fallback, issue detail images, upload preview, and modal scrolling.

## Tests

- `backend/tests/test_phase9_image_security.py` covers valid local uploads, external URLs, path traversal, query strings, missing images, issue association, and resolution evidence sanitization.
- `npm run lint` exits 0 with pre-existing warnings.
- `npm run build` passes.
