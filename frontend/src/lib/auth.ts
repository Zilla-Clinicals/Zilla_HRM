import { api, setAccessToken } from "./apiClient";
import type { Me } from "../shared/types";

interface TokenOut {
  access_token: string;
  token_type: string;
}

interface LoginOut {
  access_token: string | null;
  token_type: string;
  mfa_required: boolean;
  mfa_token: string | null;
}

/**
 * First login step. Returns an `mfaToken` (and no session) when the account has
 * two-factor enabled — the caller must follow up with `verifyMfa`.
 */
export async function login(
  email: string,
  password: string,
): Promise<{ mfaRequired: boolean; mfaToken: string | null }> {
  const res = await api.post<LoginOut>("/api/auth/login", { email, password }, true);
  if (res.mfa_required) {
    return { mfaRequired: true, mfaToken: res.mfa_token };
  }
  setAccessToken(res.access_token);
  return { mfaRequired: false, mfaToken: null };
}

/** Second login step: exchange the challenge + authenticator/recovery code for a session. */
export async function verifyMfa(mfaToken: string, code: string): Promise<void> {
  const res = await api.post<TokenOut>(
    "/api/auth/login/verify",
    { mfa_token: mfaToken, code },
    true,
  );
  setAccessToken(res.access_token);
}

export async function acceptInvite(
  token: string,
  full_name: string,
  password: string,
): Promise<void> {
  const res = await api.post<TokenOut>(
    "/api/auth/accept-invite",
    { token, full_name, password },
    true,
  );
  setAccessToken(res.access_token);
}

export async function logout(): Promise<void> {
  try {
    await api.post("/api/auth/logout");
  } finally {
    setAccessToken(null);
  }
}

// Attempt to restore a session via the refresh cookie on app boot.
export async function bootstrapSession(): Promise<Me | null> {
  try {
    const res = await api.post<TokenOut>("/api/auth/refresh", undefined, true);
    setAccessToken(res.access_token);
    return await api.get<Me>("/api/users/me");
  } catch {
    setAccessToken(null);
    return null;
  }
}

export function forgotPassword(email: string) {
  return api.post("/api/auth/forgot-password", { email }, true);
}

export function resetPassword(token: string, new_password: string) {
  return api.post("/api/auth/reset-password", { token, new_password }, true);
}
