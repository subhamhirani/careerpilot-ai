// ============================================================
// CareerPilot - API Client
// ============================================================

const RAW_API_BASE = process.env.NEXT_PUBLIC_API_URL || '';
const API_BASE = RAW_API_BASE.replace(/\/api\/?$/, '').replace(/\/$/, '');

interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
  const url = new URL(`${API_BASE}/api${endpoint}`, typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000');

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        url.searchParams.set(key, String(value));
      }
    });
  }

  return url.pathname + url.search;
}

async function getAuthHeaders(): Promise<HeadersInit> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('careerpilot_token') || sessionStorage.getItem('careerpilot_token');
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }
  }

  return headers;
}

async function request<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { params, ...fetchOpts } = options;
  const url = buildUrl(endpoint, params);

  try {
    const res = await fetch(url, {
      ...fetchOpts,
      headers: {
        ...(await getAuthHeaders()),
        ...fetchOpts.headers,
      },
    });

    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}`;
      try {
        const errorBody = await res.json();
        errorMessage = errorBody.detail || errorBody.error || errorBody.message || errorMessage;
      } catch {
        // ignore parse error
      }
      throw new ApiError(errorMessage, res.status);
    }

    // Handle 204 No Content
    if (res.status === 204) {
      return {} as T;
    }

    return await res.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }
}

// --- Public API ---

export const api = {
  get: <T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>) =>
    request<T>(endpoint, { method: 'GET', params }),

  post: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),

  postForm: async <T>(endpoint: string, body: FormData) => {
    const url = buildUrl(endpoint);
    const headers = await getAuthHeaders();
    delete (headers as Record<string, string>)['Content-Type'];
    const res = await fetch(url, { method: 'POST', headers, body });
    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}`;
      try {
        const errorBody = await res.json();
        errorMessage = errorBody.detail || errorBody.error || errorBody.message || errorMessage;
      } catch {}
      throw new ApiError(errorMessage, res.status);
    }
    return await res.json() as T;
  },

  put: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),

  patch: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined }),

  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: 'DELETE' }),
};

// --- Auth helpers ---

export function setAuthToken(token: string, persist = false): void {
  if (persist) {
    localStorage.setItem('careerpilot_token', token);
  } else {
    sessionStorage.setItem('careerpilot_token', token);
  }
}

export function clearAuthToken(): void {
  localStorage.removeItem('careerpilot_token');
  sessionStorage.removeItem('careerpilot_token');
}

export function getAuthToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('careerpilot_token') || sessionStorage.getItem('careerpilot_token');
  }
  return null;
}

export { ApiError };
