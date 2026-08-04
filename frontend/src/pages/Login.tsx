import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthCard } from "../components/AuthCard";
import { ErrorText } from "../components/ui";
import { useAuth } from "../auth/useAuth";

export function Login() {
  const { signIn, completeMfa, me } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Second-factor challenge state (set once the password step reports mfa_required).
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState("");

  if (me) navigate("/", { replace: true });

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await signIn(email, password);
      if (res.mfaRequired) {
        setMfaToken(res.mfaToken);
      } else {
        navigate("/", { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  const onVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mfaToken) return;
    setError(null);
    setBusy(true);
    try {
      await completeMfa(mfaToken, code.trim());
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  };

  if (mfaToken) {
    return (
      <AuthCard title="Two-factor authentication" subtitle="Enter the 6-digit code from your authenticator app">
        <form onSubmit={onVerify} className="space-y-4">
          <div>
            <label className="label" htmlFor="code">
              Authentication code
            </label>
            <input
              id="code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              className="input text-center text-lg tracking-[0.3em]"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="123456"
              required
              autoFocus
            />
            <p className="mt-2 text-xs text-slate-500">
              Lost your device? Enter one of your recovery codes instead.
            </p>
          </div>
          <ErrorText message={error} />
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? "Verifying…" : "Verify"}
          </button>
          <button
            type="button"
            className="w-full text-center text-sm text-slate-500 hover:underline"
            onClick={() => {
              setMfaToken(null);
              setCode("");
              setError(null);
            }}
          >
            Back to sign in
          </button>
        </form>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Sign in" subtitle="Welcome back">
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
        </div>
        <div>
          <label className="label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <ErrorText message={error} />
        <button type="submit" className="btn-primary w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <div className="text-center text-sm">
          <Link to="/forgot-password" className="text-brand-600 hover:underline">
            Forgot your password?
          </Link>
        </div>
      </form>
    </AuthCard>
  );
}
