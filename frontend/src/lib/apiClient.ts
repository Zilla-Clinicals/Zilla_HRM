const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

let accessToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Single-flight refresh so concurrent 401s share one refresh call.
let refreshInFlight: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${BASE}/api/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!res.ok) return false;
        const data = (await res.json()) as { access_token: string };
        accessToken = data.access_token;
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  // Skip the auto-refresh retry (used by auth endpoints themselves).
  skipAuth?: boolean;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const doFetch = () => {
    const headers: Record<string, string> = {};
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    if (accessToken && !opts.skipAuth) headers["Authorization"] = `Bearer ${accessToken}`;
    return fetch(`${BASE}${path}`, {
      method: opts.method ?? "GET",
      credentials: "include",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  };

  let res = await doFetch();

  if (res.status === 401 && !opts.skipAuth) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      res = await doFetch();
    } else {
      onUnauthorized?.();
      throw new ApiError(401, "Session expired");
    }
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;

  if (!res.ok) {
    const detail = (data && (data.detail ?? data.message)) || res.statusText;
    throw new ApiError(res.status, typeof detail === "string" ? detail : "Request failed");
  }
  return data as T;
}

// Authenticated binary fetch (images, downloads). Returns null on 404/failure.
export async function fetchBlob(path: string): Promise<Blob | null> {
  const doFetch = () =>
    fetch(`${BASE}${path}`, {
      credentials: "include",
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    });
  let res = await doFetch();
  if (res.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) res = await doFetch();
    else {
      onUnauthorized?.();
      return null;
    }
  }
  if (!res.ok) return null;
  return res.blob();
}

// Multipart upload (files). Browser sets the multipart boundary — don't set Content-Type.
async function requestForm<T>(path: string, form: FormData, method: string): Promise<T> {
  const doFetch = () => {
    const headers: Record<string, string> = {};
    if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
    return fetch(`${BASE}${path}`, { method, credentials: "include", headers, body: form });
  };
  let res = await doFetch();
  if (res.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) res = await doFetch();
    else {
      onUnauthorized?.();
      throw new ApiError(401, "Session expired");
    }
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!res.ok) {
    const detail = (data && (data.detail ?? data.message)) || res.statusText;
    throw new ApiError(res.status, typeof detail === "string" ? detail : "Upload failed");
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, skipAuth = false) =>
    request<T>(path, { method: "POST", body, skipAuth }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  form: <T>(path: string, form: FormData, method = "POST") => requestForm<T>(path, form, method),
};
