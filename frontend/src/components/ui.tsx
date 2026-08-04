import { createPortal } from "react-dom";
import type {
  CycleStatus,
  EmployeeStatus,
  GoalStatus,
  KpiStatus,
  ReviewStatus,
} from "../shared/types";

const goalStatusMeta: Record<GoalStatus, { label: string; cls: string }> = {
  not_started: { label: "Not started", cls: "bg-slate-100 text-slate-600" },
  in_progress: { label: "In progress", cls: "bg-amber-100 text-amber-700" },
  completed: { label: "Completed", cls: "bg-emerald-100 text-emerald-700" },
  cancelled: { label: "Cancelled", cls: "bg-slate-200 text-slate-500" },
};

export function GoalStatusBadge({ status }: { status: GoalStatus }) {
  const m = goalStatusMeta[status];
  return <span className={`badge ${m.cls}`}>{m.label}</span>;
}

const kpiStatusMeta: Record<KpiStatus, { label: string; cls: string }> = {
  met: { label: "Met", cls: "bg-emerald-100 text-emerald-700" },
  partial: { label: "Partial", cls: "bg-amber-100 text-amber-700" },
  not_met: { label: "Not Met", cls: "bg-red-100 text-red-700" },
};

export function KpiStatusBadge({ status }: { status: KpiStatus }) {
  const m = kpiStatusMeta[status];
  return <span className={`badge ${m.cls}`}>{m.label}</span>;
}

const employeeColors: Record<EmployeeStatus, string> = {
  active: "bg-emerald-100 text-emerald-700",
  pending: "bg-amber-100 text-amber-700",
  inactive: "bg-slate-200 text-slate-500",
};

export function EmployeeStatusBadge({ status }: { status: EmployeeStatus }) {
  return <span className={`badge ${employeeColors[status]}`}>{status}</span>;
}

const cycleColors: Record<CycleStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  open: "bg-emerald-100 text-emerald-700",
  closed: "bg-slate-200 text-slate-600",
};

const reviewColors: Record<ReviewStatus, string> = {
  not_started: "bg-slate-100 text-slate-600",
  in_progress: "bg-amber-100 text-amber-700",
  submitted: "bg-emerald-100 text-emerald-700",
};

export function CycleStatusBadge({ status }: { status: CycleStatus }) {
  return <span className={`badge ${cycleColors[status]}`}>{status}</span>;
}

export function ReviewStatusBadge({ status }: { status: ReviewStatus }) {
  return (
    <span className={`badge ${reviewColors[status]}`}>{status.replace("_", " ")}</span>
  );
}

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  // Rendered through a portal to <body> so the overlay's `position: fixed` is
  // anchored to the viewport. Otherwise an animated ancestor (the page wrapper
  // keeps a persistent `transform` from `animate-fade-in-up`) becomes the
  // containing block and the modal gets clipped by the page's content box.
  return createPortal(
    <div
      className="fixed inset-0 z-50 flex animate-fade-in items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      {/* Capped to the screen height and centered; header stays put, body scrolls. */}
      <div
        className="card flex max-h-[90vh] w-full max-w-lg animate-scale-in flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-slate-100 px-6 py-4">
          <h2 className="text-lg font-bold text-slate-800">{title}</h2>
          <button
            onClick={onClose}
            className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        {/* min-h-0 lets this flex child actually shrink + scroll instead of
            forcing the card past the screen (the flexbox overflow gotcha). */}
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

export function ErrorText({ message }: { message: string | null }) {
  if (!message) return null;
  return <p className="text-sm text-red-600">{message}</p>;
}
