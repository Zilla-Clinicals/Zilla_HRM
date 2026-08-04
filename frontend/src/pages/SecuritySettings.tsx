import { useState } from "react";
import QRCode from "qrcode";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorText } from "../components/ui";
import { api } from "../lib/apiClient";
import { useAuth } from "../auth/useAuth";

export function SecuritySettings() {
  const { me, loading } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);

  if (loading) return <LoadingSpinner full />;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setOk(false);
    if (next !== confirm) {
      setError("New passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await api.post("/api/users/me/password", {
        current_password: current,
        new_password: next,
      });
      setOk(true);
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-xl font-semibold text-slate-800">Settings</h1>

      <div className="card p-6">
        <h2 className="text-sm font-semibold text-slate-700">Account</h2>
        <p className="mt-2 text-sm text-slate-500">{me?.user.email}</p>
        <p className="text-sm capitalize text-slate-500">
          Role: {me?.user.role.replace("_", " ")}
        </p>
      </div>

      <TwoFactorSection />

      <div className="card p-6">
        <h2 className="mb-4 text-sm font-semibold text-slate-700">Change password</h2>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="label">Current password</label>
            <input
              type="password"
              className="input"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label">New password</label>
            <input
              type="password"
              className="input"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              minLength={8}
              required
            />
          </div>
          <div>
            <label className="label">Confirm new password</label>
            <input
              type="password"
              className="input"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              minLength={8}
              required
            />
          </div>
          <ErrorText message={error} />
          {ok && <p className="text-sm text-emerald-700">Password updated.</p>}
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Updating…" : "Update password"}
          </button>
        </form>
      </div>
    </div>
  );
}

interface SetupState {
  secret: string;
  otpauth_uri: string;
  qrDataUrl: string;
}

function TwoFactorSection() {
  const { me, refreshMe } = useAuth();
  const enabled = me?.user.mfa_enabled ?? false;

  const [setup, setSetup] = useState<SetupState | null>(null);
  const [code, setCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [disablePassword, setDisablePassword] = useState("");
  const [showDisable, setShowDisable] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const beginSetup = async () => {
    setError(null);
    setBusy(true);
    try {
      const res = await api.post<{ secret: string; otpauth_uri: string }>(
        "/api/users/me/2fa/setup",
      );
      const qrDataUrl = await QRCode.toDataURL(res.otpauth_uri, { margin: 1, width: 200 });
      setSetup({ ...res, qrDataUrl });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start 2FA setup");
    } finally {
      setBusy(false);
    }
  };

  const confirmEnable = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await api.post<{ recovery_codes: string[] }>("/api/users/me/2fa/enable", {
        code: code.trim(),
      });
      setRecoveryCodes(res.recovery_codes);
      setSetup(null);
      setCode("");
      await refreshMe();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That code wasn't valid");
    } finally {
      setBusy(false);
    }
  };

  const disable = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.post("/api/users/me/2fa/disable", { password: disablePassword });
      setDisablePassword("");
      setShowDisable(false);
      await refreshMe();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not disable 2FA");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-700">Two-factor authentication</h2>
          <p className="mt-1 text-sm text-slate-500">
            Protect your account with a code from an authenticator app (Google Authenticator,
            Microsoft Authenticator, 1Password, Authy…).
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
            enabled
              ? "bg-emerald-100 text-emerald-700"
              : "bg-slate-100 text-slate-500"
          }`}
        >
          {enabled ? "On" : "Off"}
        </span>
      </div>

      {/* One-time recovery codes shown right after enabling. */}
      {recoveryCodes && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-800">
            Save your recovery codes
          </p>
          <p className="mt-1 text-xs text-amber-700">
            Each code works once if you lose your authenticator. Store them somewhere safe —
            you won't see them again.
          </p>
          <div className="mt-3 grid grid-cols-2 gap-2 font-mono text-sm text-slate-700">
            {recoveryCodes.map((c) => (
              <span key={c} className="rounded bg-white px-2 py-1 text-center">
                {c}
              </span>
            ))}
          </div>
          <button
            type="button"
            className="btn-secondary mt-3"
            onClick={() => navigator.clipboard?.writeText(recoveryCodes.join("\n"))}
          >
            Copy codes
          </button>
          <button
            type="button"
            className="btn-primary ml-2 mt-3"
            onClick={() => setRecoveryCodes(null)}
          >
            Done
          </button>
        </div>
      )}

      {/* Enabled + not currently disabling → offer disable. */}
      {enabled && !recoveryCodes && !showDisable && (
        <button type="button" className="btn-secondary mt-4" onClick={() => setShowDisable(true)}>
          Turn off two-factor
        </button>
      )}

      {enabled && showDisable && (
        <form onSubmit={disable} className="mt-4 space-y-3">
          <div>
            <label className="label">Confirm your password to turn off 2FA</label>
            <input
              type="password"
              className="input"
              value={disablePassword}
              onChange={(e) => setDisablePassword(e.target.value)}
              required
            />
          </div>
          <ErrorText message={error} />
          <div className="flex gap-2">
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Turning off…" : "Turn off 2FA"}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setShowDisable(false);
                setDisablePassword("");
                setError(null);
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Disabled + not mid-setup → offer enable. */}
      {!enabled && !setup && (
        <button type="button" className="btn-primary mt-4" onClick={beginSetup} disabled={busy}>
          {busy ? "Preparing…" : "Set up two-factor"}
        </button>
      )}

      {/* Disabled + mid-setup → QR + confirm code. */}
      {!enabled && setup && (
        <div className="mt-4 space-y-4">
          <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-600">
            <li>Open your authenticator app and scan this QR code.</li>
            <li>Enter the 6-digit code it shows to finish.</li>
          </ol>
          <div className="flex flex-col items-center gap-3 rounded-lg border border-slate-200 p-4">
            <img src={setup.qrDataUrl} alt="2FA QR code" className="h-48 w-48" />
            <p className="text-xs text-slate-500">Can't scan? Enter this key manually:</p>
            <code className="break-all rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-700">
              {setup.secret}
            </code>
          </div>
          <form onSubmit={confirmEnable} className="space-y-3">
            <div>
              <label className="label">Verification code</label>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                className="input"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="123456"
                required
              />
            </div>
            <ErrorText message={error} />
            <div className="flex gap-2">
              <button type="submit" className="btn-primary" disabled={busy}>
                {busy ? "Verifying…" : "Verify & enable"}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  setSetup(null);
                  setCode("");
                  setError(null);
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Errors from the enable-start / setup path (outside the forms). */}
      {!setup && !showDisable && <ErrorText message={error} />}
    </div>
  );
}
