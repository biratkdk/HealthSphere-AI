import axios from "axios";

const API_PREFIX = "/api/v1";

const sanitizeBaseURL = (value) => (typeof value === "string" ? value.trim() : "");

const legacyBaseURL =
  typeof process !== "undefined" && process.env ? sanitizeBaseURL(process.env.REACT_APP_API_BASE_URL) : "";

const readDocumentBaseURL = () => {
  if (typeof document === "undefined") {
    return "";
  }
  const meta = document.querySelector('meta[name="healthsphere-api-base"]');
  return sanitizeBaseURL(meta?.getAttribute("content"));
};

const resolveHostedBaseURL = () => {
  if (typeof window === "undefined") {
    return "";
  }

  const documentBaseURL = readDocumentBaseURL();
  if (documentBaseURL) {
    return documentBaseURL;
  }

  const { hostname, origin } = window.location;
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }

  return origin;
};

const resolvedBaseURL =
  sanitizeBaseURL(import.meta.env.VITE_API_BASE_URL) ||
  legacyBaseURL ||
  resolveHostedBaseURL() ||
  "http://localhost:8000";

const serviceBaseURL = resolvedBaseURL.replace(/\/$/, "");
const baseURL = `${serviceBaseURL}${API_PREFIX}`;

export const api = axios.create({
  baseURL,
  timeout: 15000,
  withCredentials: true,
});

// ---------------------------------------------------------------------------
// 401 auto-refresh interceptor
// When an API call returns 401 the interceptor attempts a silent token refresh
// (using the HttpOnly refresh cookie) and retries the original request once.
// If the refresh also fails the user is treated as logged out.
// ---------------------------------------------------------------------------
let _isRefreshing = false;
let _refreshQueue = [];

const _processQueue = (error) => {
  _refreshQueue.forEach((cb) => cb(error));
  _refreshQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    // Only intercept 401, never retry requests that already retried, and skip
    // auth endpoints (refresh/logout) to avoid infinite loops.
    const isAuthEndpoint =
      original?.url?.includes("/auth/refresh") ||
      original?.url?.includes("/auth/logout") ||
      original?.url?.includes("/auth/token");

    if (error?.response?.status !== 401 || original?._retried || isAuthEndpoint) {
      return Promise.reject(error);
    }

    original._retried = true;

    if (_isRefreshing) {
      // Queue this request until the in-flight refresh completes
      return new Promise((resolve, reject) => {
        _refreshQueue.push((refreshError) => {
          if (refreshError) {
            reject(refreshError);
          } else {
            resolve(api(original));
          }
        });
      });
    }

    _isRefreshing = true;
    try {
      await api.post("/auth/refresh");
      _processQueue(null);
      return api(original);
    } catch (refreshError) {
      _processQueue(refreshError);
      return Promise.reject(refreshError);
    } finally {
      _isRefreshing = false;
    }
  }
);

// No user data is persisted to localStorage — authentication state is held
// exclusively in memory and backed by HttpOnly session cookies, eliminating
// the XSS attack surface of localStorage-based credential storage.
export const clearAuthSession = () => {
  // Cookie clearing is handled server-side via /auth/logout.
  // This is a no-op kept for call-site compatibility.
};

// Map raw server/network errors to user-safe messages.
// Never forward raw server error strings to the UI — they may contain
// stack traces, database schema details, or internal paths.
const SERVER_ERROR_MESSAGES = {
  400: "The request was invalid. Please check your input and try again.",
  401: "Your session has expired. Please sign in again.",
  403: "You do not have permission to perform this action.",
  404: "The requested resource was not found.",
  409: "A conflict occurred. The record may already exist.",
  422: "The submitted data could not be validated. Please review your input.",
  429: "Too many requests. Please wait a moment and try again.",
  500: "An unexpected error occurred on the server. Please try again later.",
  502: "The service is temporarily unavailable. Please try again shortly.",
  503: "The service is currently unavailable. Please try again later.",
};

export const getRequestErrorMessage = (error, fallbackMessage = "Request failed.") => {
  if (error?.message === "Network Error") {
    return "Unable to reach the service. Please check your connection and try again.";
  }

  const status = error?.response?.status;
  if (status && SERVER_ERROR_MESSAGES[status]) {
    // For auth errors, surface the server message (it's intentionally user-facing)
    if (status === 401 || status === 403) {
      return error?.response?.data?.detail || SERVER_ERROR_MESSAGES[status];
    }
    // For 429 (rate limit), the server message is also safe
    if (status === 429) {
      return error?.response?.data?.detail || SERVER_ERROR_MESSAGES[status];
    }
    return SERVER_ERROR_MESSAGES[status];
  }

  return fallbackMessage;
};

const triggerBrowserDownload = (blob, filename) => {
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
};

export const apiFetcher = async ([resource, ...args]) => {
  switch (resource) {
    case "patients":
      return getPatients(args[0]);
    case "patient":
      return getPatient(args[0]);
    case "patientSummary":
      return getPatientSummary(args[0]);
    case "patientTimeline":
      return getPatientTimeline(args[0], args[1]);
    case "patientTasks":
      return getPatientTasks(args[0]);
    case "patientHandoffs":
      return getPatientHandoffs(args[0], args[1]);
    case "patientImaging":
      return getPatientImagingStudies(args[0], args[1]);
    case "alerts":
      return getAlerts();
    case "analytics":
      return getAnalyticsOverview();
    case "notifications":
      return getNotifications(args[0], args[1]);
    case "models":
      return getModelRegistry();
    case "reportJobs":
      return getReportJobs(args[0]);
    case "reportJob":
      return getReportJob(args[0]);
    case "authSessions":
      return getAuthSessions();
    case "auditLogs":
      return getAuditLogs(args[0]);
    case "adminUsers":
      return getAdminUsers(args[0]);
    case "inviteCodes":
      return getInviteCodes(args[0]);
    default:
      throw new Error(`Unknown data resource: ${resource}`);
  }
};

export const getAuthProviders = async () => {
  const response = await api.get("/auth/providers");
  return response.data;
};

export const login = async (username, password) => {
  const formData = new URLSearchParams();
  formData.set("username", username);
  formData.set("password", password);

  const response = await api.post("/auth/token", formData, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });
  return response.data;
};

export const signup = async (payload) => {
  const response = await api.post("/auth/signup", payload);
  return response.data;
};

export const refreshAuthSession = async () => {
  const response = await api.post("/auth/refresh");
  return response.data;
};

export const logoutRequest = async () => {
  await api.post("/auth/logout");
};

export const getCurrentUser = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};

export const updateCurrentUser = async (payload) => {
  const response = await api.patch("/auth/me", payload);
  return response.data;
};

export const getAuthSessions = async () => {
  const response = await api.get("/auth/sessions");
  return response.data;
};

export const revokeAuthSession = async (sessionId) => {
  await api.post(`/auth/sessions/${sessionId}/revoke`);
};

export const revokeAllAuthSessions = async () => {
  await api.post("/auth/sessions/revoke-all");
};

export const getOperationsStreamToken = async () => {
  const response = await api.get("/events/stream-token");
  return response.data;
};

export const getOperationsStreamUrl = (streamToken) =>
  `${baseURL}/events/operations?stream_token=${encodeURIComponent(streamToken)}`;

export const getPatients = async (query = "") => {
  const suffix = query ? `?query=${encodeURIComponent(query)}&limit=200` : "";
  const response = await api.get(`/patients${suffix}`);
  return response.data;
};

export const getPatient = async (patientId) => {
  const response = await api.get(`/patients/${patientId}`);
  return response.data;
};

export const getPatientSummary = async (patientId) => {
  const response = await api.get(`/patients/${patientId}/summary`);
  return response.data;
};

export const getPatientTimeline = async (patientId, limit = 40) => {
  const response = await api.get(`/patients/${patientId}/timeline?limit=${limit}`);
  return response.data;
};

export const getPatientTasks = async (patientId) => {
  const response = await api.get(`/patients/${patientId}/tasks`);
  return response.data;
};

export const createPatientTask = async (patientId, payload) => {
  const response = await api.post(`/patients/${patientId}/tasks`, payload);
  return response.data;
};

export const updatePatientTask = async (patientId, taskId, payload) => {
  const response = await api.patch(`/patients/${patientId}/tasks/${taskId}`, payload);
  return response.data;
};

export const getPatientHandoffs = async (patientId, limit = 12) => {
  const response = await api.get(`/patients/${patientId}/handoffs?limit=${limit}`);
  return response.data;
};

export const createPatientHandoff = async (patientId, payload) => {
  const response = await api.post(`/patients/${patientId}/handoffs`, payload);
  return response.data;
};

export const getPatientImagingStudies = async (patientId, limit = 6) => {
  const response = await api.get(`/patients/${patientId}/imaging/studies?limit=${limit}`);
  return response.data;
};

export const getAlerts = async () => {
  const response = await api.get("/alerts");
  return response.data;
};

export const acknowledgeAlert = async (alertId) => {
  const response = await api.post(`/alerts/${alertId}/acknowledge`);
  return response.data;
};

export const getAnalyticsOverview = async () => {
  const response = await api.get("/analytics/overview");
  return response.data;
};

export const getNotifications = async (limit = 20, unreadOnly = false) => {
  const response = await api.get(`/notifications?limit=${limit}&unread_only=${unreadOnly}`);
  return response.data;
};

export const markNotificationRead = async (notificationId) => {
  const response = await api.post(`/notifications/${notificationId}/read`);
  return response.data;
};

export const getModelRegistry = async () => {
  const response = await api.get("/models/registry");
  return response.data;
};

export const analyzeImaging = async (file, patientId) => {
  if (!patientId) {
    throw new Error("Select a patient before submitting an imaging study.");
  }
  const formData = new FormData();
  formData.append("file", file);
  formData.append("patient_id", String(patientId));
  const response = await api.post("/analyze/imaging", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const createReportJob = async (patientId, idempotencyKey) => {
  const headers = idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined;
  const response = await api.post(`/reports/patient/${patientId}`, undefined, { headers });
  return response.data;
};

export const getReportJob = async (jobId) => {
  const response = await api.get(`/reports/jobs/${jobId}`);
  return response.data;
};

export const getReportJobs = async (limit = 25) => {
  const response = await api.get(`/reports/jobs?limit=${limit}`);
  return response.data;
};

export const getAuditLogs = async (limit = 50) => {
  const response = await api.get(`/admin/audit-logs?limit=${limit}`);
  return response.data;
};

export const getAdminUsers = async (limit = 100) => {
  const response = await api.get(`/admin/users?limit=${limit}`);
  return response.data;
};

export const updateAdminUserStatus = async (username, isActive) => {
  const response = await api.patch(`/admin/users/${username}/status`, { is_active: isActive });
  return response.data;
};

export const updateAdminUserRole = async (username, role) => {
  const response = await api.patch(`/admin/users/${username}/role`, { role });
  return response.data;
};

export const getInviteCodes = async (limit = 50) => {
  const response = await api.get(`/admin/invites?limit=${limit}`);
  return response.data;
};

export const createInviteCode = async (payload) => {
  const response = await api.post("/admin/invites", payload);
  return response.data;
};

export const downloadReportArtifact = async (jobId) => {
  const response = await api.get(`/reports/jobs/${jobId}/artifact`, { responseType: "blob" });
  const blob = new Blob([response.data], { type: response.headers["content-type"] || "application/json" });
  triggerBrowserDownload(blob, `${jobId}.json`);
};

export const downloadImagingStudy = async (studyId, filename = "study.bin") => {
  const response = await api.get(`/imaging/studies/${studyId}/content`, { responseType: "blob" });
  const blob = new Blob([response.data], {
    type: response.headers["content-type"] || "application/octet-stream",
  });
  triggerBrowserDownload(blob, filename);
};
