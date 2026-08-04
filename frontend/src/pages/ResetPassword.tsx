import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthCard } from "../components/AuthCard";
import { ErrorText } from "../components/ui";
import { resetPassword } from "../lib/auth";

export function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await resetPassword(token, password);
      setDone(true);
      setTimeout(() => navigate("/login", { replace: true }), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reset password");
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <AuthCard title="Invalid reset link">
        <p className="text-sm text-slate-600">This reset link is missing its token.</p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Reset password" subtitle="Choose a new password">
      {done ? (
        <p className="text-center text-sm text-emerald-700">
          Password updated. Redirecting to sign in…
        </p>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="password">
              New password
            </label>
            <input
              id="password"
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
              autoFocus
            />
          </div>
          <div>
            <label className="label" htmlFor="confirm">
              Confirm password
            </label>
            <input
              id="confirm"
              type="password"
              className="input"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              minLength={8}
              required
            />
          </div>
          <ErrorText message={error} />
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? "Updating…" : "Update password"}
          </button>
          <div className="text-center text-sm">
            <Link to="/login" className="text-brand-600 hover:underline">
              Back to sign in
            </Link>
          </div>
        </form>
      )}
    </AuthCard>
  );
}
