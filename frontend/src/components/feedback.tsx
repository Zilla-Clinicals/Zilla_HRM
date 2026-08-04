import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

type ToastType = "success" | "error" | "info";

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ConfirmOptions {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
}

interface FeedbackApi {
  toast: (type: ToastType, message: string) => void;
  confirm: (opts: ConfirmOptions) => Promise<boolean>;
}

const FeedbackContext = createContext<FeedbackApi | null>(null);

const toastStyles: Record<ToastType, { box: string; bar: string; icon: string }> = {
  success: {
    box: "border-emerald-100 bg-white text-emerald-800",
    bar: "bg-emerald-500",
    icon: "✓",
  },
  error: { box: "border-rose-100 bg-white text-rose-800", bar: "bg-rose-500", icon: "!" },
  info: { box: "border-slate-200 bg-white text-slate-700", bar: "bg-brand-500", icon: "i" },
};

export function FeedbackProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [confirmState, setConfirmState] = useState<
    (ConfirmOptions & { resolve: (v: boolean) => void }) | null
  >(null);
  const nextId = useRef(1);

  const toast = useCallback((type: ToastType, message: string) => {
    const id = nextId.current++;
    setToasts((t) => [...t, { id, type, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  const confirm = useCallback(
    (opts: ConfirmOptions) =>
      new Promise<boolean>((resolve) => setConfirmState({ ...opts, resolve })),
    [],
  );

  const closeConfirm = (value: boolean) => {
    confirmState?.resolve(value);
    setConfirmState(null);
  };

  const api = useMemo<FeedbackApi>(() => ({ toast, confirm }), [toast, confirm]);

  return (
    <FeedbackContext.Provider value={api}>
      {children}

      <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-80 flex-col gap-2.5">
        {toasts.map((t) => {
          const s = toastStyles[t.type];
          return (
            <div
              key={t.id}
              className={`pointer-events-auto flex animate-slide-in-right items-center gap-3 overflow-hidden rounded-xl border pl-3 pr-4 py-3 text-sm shadow-card ${s.box}`}
            >
              <span
                className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold text-white ${s.bar}`}
              >
                {s.icon}
              </span>
              <span className="font-medium">{t.message}</span>
            </div>
          );
        })}
      </div>

      {confirmState && (
        <div className="fixed inset-0 z-50 flex animate-fade-in items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <div className="card w-full max-w-sm animate-scale-in p-6">
            <h2 className="text-lg font-bold text-slate-800">{confirmState.title}</h2>
            {confirmState.message && (
              <p className="mt-2 text-sm text-slate-600">{confirmState.message}</p>
            )}
            <div className="mt-5 flex justify-end gap-2">
              <button className="btn-secondary" onClick={() => closeConfirm(false)}>
                {confirmState.cancelLabel ?? "Cancel"}
              </button>
              <button
                className={confirmState.danger ? "btn-danger" : "btn-primary"}
                onClick={() => closeConfirm(true)}
              >
                {confirmState.confirmLabel ?? "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </FeedbackContext.Provider>
  );
}

export function useFeedback() {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error("useFeedback must be used within FeedbackProvider");
  return ctx;
}
