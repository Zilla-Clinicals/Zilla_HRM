import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { useFeedback } from "./feedback";
import { Modal } from "./ui";

/**
 * Automatic sign-out after a period of inactivity — standard practice for apps
 * holding sensitive HR/PII data. The user is warned shortly before the deadline
 * and can extend; if they stay idle they are signed out (which also revokes the
 * refresh token server-side via /logout). Activity is synced across tabs, so
 * staying active in one tab keeps every tab alive.
 */
const IDLE_LIMIT_MS = 30 * 60 * 1000; // sign out after 30 min of inactivity
const WARN_BEFORE_MS = 60 * 1000; // show the "still there?" warning 60s before
const STORAGE_KEY = "hrm_last_activity"; // cross-tab activity heartbeat

const ACTIVITY_EVENTS = [
  "mousemove",
  "mousedown",
  "keydown",
  "scroll",
  "touchstart",
  "wheel",
  "click",
] as const;

export function SessionTimeout() {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const { toast } = useFeedback();

  const lastActivity = useRef(Date.now());
  const lastWrite = useRef(0);
  const signingOut = useRef(false);

  const [warnOpen, setWarnOpen] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);

  const markActive = useCallback(() => {
    const now = Date.now();
    lastActivity.current = now;
    // Throttle cross-tab writes; every tab's "storage" listener picks this up.
    if (now - lastWrite.current >= 2000) {
      lastWrite.current = now;
      try {
        localStorage.setItem(STORAGE_KEY, String(now));
      } catch {
        /* storage may be unavailable (private mode) — local ref still works */
      }
    }
  }, []);

  const doSignOut = useCallback(async () => {
    if (signingOut.current) return;
    signingOut.current = true;
    setWarnOpen(false);
    await signOut();
    toast("info", "You were signed out due to inactivity.");
    navigate("/login", { replace: true });
  }, [signOut, toast, navigate]);

  // Reset the idle clock on any user activity + sync from other tabs.
  useEffect(() => {
    const onActivity = () => markActive();
    ACTIVITY_EVENTS.forEach((e) =>
      window.addEventListener(e, onActivity, { passive: true }),
    );

    const onStorage = (ev: StorageEvent) => {
      if (ev.key === STORAGE_KEY && ev.newValue) {
        lastActivity.current = Number(ev.newValue);
      }
    };
    window.addEventListener("storage", onStorage);

    markActive(); // seed the heartbeat on mount
    return () => {
      ACTIVITY_EVENTS.forEach((e) => window.removeEventListener(e, onActivity));
      window.removeEventListener("storage", onStorage);
    };
  }, [markActive]);

  // Evaluate idle time once a second.
  useEffect(() => {
    const id = setInterval(() => {
      const remaining = IDLE_LIMIT_MS - (Date.now() - lastActivity.current);
      if (remaining <= 0) {
        void doSignOut();
      } else if (remaining <= WARN_BEFORE_MS) {
        setSecondsLeft(Math.ceil(remaining / 1000));
        setWarnOpen(true);
      } else {
        setWarnOpen((open) => (open ? false : open));
      }
    }, 1000);
    return () => clearInterval(id);
  }, [doSignOut]);

  if (!warnOpen) return null;

  return (
    <Modal title="Still there?" onClose={markActive}>
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          You've been inactive for a while. For your security you'll be signed out in{" "}
          <span className="font-semibold text-slate-800">{secondsLeft}s</span>.
        </p>
        <div className="flex justify-end gap-2">
          <button className="btn-secondary" onClick={() => void doSignOut()}>
            Sign out now
          </button>
          <button className="btn-primary" onClick={markActive}>
            Stay signed in
          </button>
        </div>
      </div>
    </Modal>
  );
}
