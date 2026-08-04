import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AuthCard } from "../components/AuthCard";
import { ErrorText } from "../components/ui";
import { acceptInvite } from "../lib/auth";
import { api } from "../lib/apiClient";
import { useAuth } from "../auth/useAuth";
import type { Me } from "../shared/types";

export function AcceptInvite() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const { setMe } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!token) {
    return (
      <AuthCard title="Invalid invitation">
        <p className="text-sm text-slate-600">
          This invitation link is missing its token. Please use the link from your email.
        </p>
      </AuthCard>
    );
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await acceptInvite(token, fullName, password);
      const me = await api.get<Me>("/api/users/me");
      setMe(me);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept invitation");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard title="Accept your invitation" subtitle="Set your name and a password">
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="label" htmlFor="name">
            Full name
          </label>
          <input
            id="name"
            className="input"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
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
            minLength={8}
            required
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
          {busy ? "Setting up…" : "Accept & continue"}
        </button>
      </form>
    </AuthCard>
  );
}
