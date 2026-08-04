import { useCallback, useEffect, useMemo, useState } from "react";
import { api, setUnauthorizedHandler } from "../lib/apiClient";
import { bootstrapSession, login, logout, verifyMfa } from "../lib/auth";
import { type Cap, roleCan } from "../lib/permissions";
import type { Me, Role } from "../shared/types";
import { AuthContext, type AuthState } from "./authContext";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setUnauthorizedHandler(() => setMe(null));
    bootstrapSession()
      .then((session) => setMe(session))
      .finally(() => setLoading(false));
    return () => setUnauthorizedHandler(null);
  }, []);

  // Returns an mfaToken when the account needs a second factor; otherwise the
  // session is established here and there is nothing more to do.
  const signIn = useCallback(async (email: string, password: string) => {
    const { mfaRequired, mfaToken } = await login(email, password);
    if (mfaRequired) return { mfaRequired: true as const, mfaToken: mfaToken! };
    setMe(await api.get<Me>("/api/users/me"));
    return { mfaRequired: false as const };
  }, []);

  const completeMfa = useCallback(async (mfaToken: string, code: string) => {
    await verifyMfa(mfaToken, code);
    setMe(await api.get<Me>("/api/users/me"));
  }, []);

  const signOut = useCallback(async () => {
    await logout();
    setMe(null);
  }, []);

  const refreshMe = useCallback(async () => {
    setMe(await api.get<Me>("/api/users/me"));
  }, []);

  const hasRole = useCallback(
    (...roles: Role[]) => (me ? roles.includes(me.user.role) : false),
    [me],
  );

  const can = useCallback((cap: Cap) => roleCan(me?.user.role ?? null, cap), [me]);

  const value = useMemo<AuthState>(
    () => ({ me, loading, signIn, completeMfa, signOut, refreshMe, setMe, hasRole, can }),
    [me, loading, signIn, completeMfa, signOut, refreshMe, hasRole, can],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
