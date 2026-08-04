import { createContext } from "react";
import type { Cap } from "../lib/permissions";
import type { Me, Role } from "../shared/types";

export type SignInResult =
  | { mfaRequired: true; mfaToken: string }
  | { mfaRequired: false };

export interface AuthState {
  me: Me | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<SignInResult>;
  completeMfa: (mfaToken: string, code: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshMe: () => Promise<void>;
  setMe: (me: Me | null) => void;
  hasRole: (...roles: Role[]) => boolean;
  can: (cap: Cap) => boolean;
}

export const AuthContext = createContext<AuthState | null>(null);
