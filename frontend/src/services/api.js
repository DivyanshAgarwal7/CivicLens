
const API_BASE = '/api';

export function getAuthToken() {
  return localStorage.getItem('civiclens_token');
}

export function setAuthToken(token) {
  localStorage.setItem('civiclens_token', token);
}

export function clearAuthToken() {
  localStorage.removeItem('civiclens_token');
  localStorage.removeItem('civiclens_user');
}

export function getStoredUser() {
  const data = localStorage.getItem('civiclens_user');
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export function setStoredUser(user) {
  localStorage.setItem('civiclens_user', JSON.stringify(user));
}

async function request(endpoint, options = {}, timeoutMs = 15000) {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  let response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('The request timed out. Please check your connection and try again.');
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }

  if (!response.ok) {
    let errorMsg = `Error ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {}
    throw new Error(errorMsg);
  }

  return response.json();
}

// Auth API
export const authApi = {
  login: async (email, password) => {
    const res = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setAuthToken(res.access_token);
    setStoredUser(res.user);
    return res;
  },

  register: async (data) => {
    const res = await request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    setAuthToken(res.access_token);
    setStoredUser(res.user);
    return res;
  },

  getMe: async () => {
    return request('/auth/me');
  },

  logout: () => {
    clearAuthToken();
  },
};

// Issues API
export const issuesApi = {
  list: async (params) => {
    const q = new URLSearchParams();
    if (params?.category) q.set('category', params.category);
    if (params?.status) q.set('status', params.status);
    if (params?.ward) q.set('ward', params.ward);
    if (params?.search) q.set('search', params.search);
    if (params?.reporter_id) q.set('reporter_id', params.reporter_id);
    return request(`/issues?${q.toString()}`);
  },

  getById: async (id) => {
    return request(`/issues/${id}`);
  },

  create: async (data

) => {
    return request('/issues', {
      method: 'POST',
      body: JSON.stringify(data),
    }, 20000);
  },

  checkDuplicate: async (data

) => {
    return request

('/issues/check-duplicate', {
      method: 'POST',
      body: JSON.stringify(data),
    }, 8000);
  },

  uploadImage: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request

('/issues/upload-image', {
      method: 'POST',
      body: formData,
    });
  },

  verify: async (issueId, comment) => {
    return request(
      `/issues/${issueId}/verify`,
      {
        method: 'POST',
        body: JSON.stringify({ comment }),
      }
    );
  },

  getVerifications: async (issueId) => {
    return request(`/issues/${issueId}/verifications`);
  },
};

// Officer API
export const officerApi = {
  getIssues: async (params) => {
    const q = new URLSearchParams();
    if (params?.status) q.set('status', params.status);
    if (params?.department) q.set('department', params.department);
    if (params?.priority) q.set('priority', params.priority);
    return request(`/officer/issues?${q.toString()}`);
  },

  getEngineers: async () => {
    return request(
      '/officer/engineers'
    );
  },

  assignIssue: async (
    issueId,
    data
  ) => {
    return request(`/officer/issues/${issueId}/assign`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  reviewPriority: async (issueId, data) => {
    return request(`/officer/issues/${issueId}/priority-review`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// Field Engineer API
export const engineerApi = {
  getTasks: async () => {
    return request('/engineer/tasks');
  },

  updateStatus: async (
    issueId,
    data
  ) => {
    return request(`/engineer/tasks/${issueId}/status`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// Analytics & Admin API
export const analyticsApi = {
  getSummary: async () => {
    return request('/analytics/summary');
  },

  getHeatmaps: async () => {
    return request

('/analytics/heatmaps');
  },
};

export const adminApi = {
  getUsers: async () => {
    return request('/admin/users');
  },

  updateUserRole: async (userId, data) => {
    return request(`/admin/users/${userId}/role`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  getDepartments: async () => {
    return request('/admin/departments');
  },

  getAuditLogs: async (limit = 50) => {
    return request(`/admin/audit-logs?limit=${limit}`);
  },
};

// Notification API
export const notificationApi = {
  list: async () => {
    return request('/notifications');
  },

  markRead: async (id) => {
    return request(`/notifications/${id}/read`, { method: 'POST' });
  },

  markAllRead: async () => {
    return request('/notifications/read-all', { method: 'POST' });
  },

  getEmailLogs: async () => {
    return request('/notifications/emails');
  },
};
