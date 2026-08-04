import { useState } from "react";
import { Link } from "react-router-dom";
import { AuthCard } from "../components/AuthCard";
import { ErrorText } from "../components/ui";
import { forgotPassword } from "../lib/auth";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard title="Forgot password" subtitle="We'll email you a reset link">
      {sent ? (
        <div className="space-y-4 text-center">
          <p className="text-sm text-slate-600">
            If an account exists for <span className="font-medium">{email}</span>, a reset
            link is on its way.
          </p>
          <Link to="/login" className="btn-secondary w-full">
            Back to sign in
          </Link>
        </div>
      ) : (
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
          <ErrorText message={error} />
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? "Sending…" : "Send reset link"}
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
