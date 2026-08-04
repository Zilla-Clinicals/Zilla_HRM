import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { useFeedback } from "../components/feedback";
import {
  CATEGORY_LABELS,
  GoalFormModal,
  ProgressBar,
} from "../components/GoalsPanel";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { GoalStatusBadge } from "../components/ui";
import { api } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type { GoalDetail as GoalDetailT, GoalStatus } from "../shared/types";

export function GoalDetail() {
  const { goalId } = useParams();
  const navigate = useNavigate();
  const { me } = useAuth();
  const { toast, confirm } = useFeedback();
  const { data: goal, loading, reload } = useApi<GoalDetailT>(
    goalId ? `/api/goals/${goalId}` : null,
  );
  const [note, setNote] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);

  if (loading) return <LoadingSpinner full />;
  if (!goal) return <p className="text-sm text-slate-500">Goal not found.</p>;

  const canEdit = me?.employee?.id === goal.employee_id;
  const canComment = !canEdit; // a manager/HR viewer reached this goal
  const locked = goal.status === "completed" || goal.status === "cancelled";
  const effProgress = progress ?? goal.progress;

  const addCheckin = async () => {
    if (!note.trim() && progress === null) return;
    setBusy(true);
    try {
      await api.post(`/api/goals/${goal.id}/checkins`, {
        note: note.trim() || null,
        progress: canEdit ? progress : null,
      });
      setNote("");
      setProgress(null);
      toast("success", canEdit ? "Check-in added." : "Comment added.");
      reload();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not save");
    } finally {
      setBusy(false);
    }
  };

  const setStatus = async (status: GoalStatus) => {
    setBusy(true);
    try {
      await api.patch(`/api/goals/${goal.id}`, {
        status,
        ...(status === "completed" ? { progress: 100 } : {}),
      });
      toast("success", "Goal updated.");
      reload();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not update");
    } finally {
      setBusy(false);
    }
  };

  const del = async () => {
    if (!(await confirm({ title: "Delete this goal?", confirmLabel: "Delete", danger: true })))
      return;
    try {
      await api.del(`/api/goals/${goal.id}`);
      toast("success", "Goal deleted.");
      navigate(-1);
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not delete");
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <button onClick={() => navigate(-1)} className="text-sm text-brand-600 hover:underline">
        ← Back
      </button>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-3">
          <h1 className="text-xl font-bold text-slate-800">{goal.title}</h1>
          <GoalStatusBadge status={goal.status} />
        </div>
        <p className="mt-1 text-xs text-slate-400">
          {goal.year} · {CATEGORY_LABELS[goal.category]}
          {goal.target_date ? ` · due ${goal.target_date}` : ""}
          {goal.employee_name ? ` · ${goal.employee_name}` : ""}
        </p>
        {goal.description && <p className="mt-3 text-sm text-slate-600">{goal.description}</p>}
        <div className="mt-4 flex items-center gap-3">
          <ProgressBar value={goal.progress} muted={goal.status === "cancelled"} />
          <span className="w-14 text-right text-sm font-semibold text-slate-700">
            {goal.progress}%
          </span>
        </div>
      </div>

      {/* Owner actions */}
      {canEdit && (
        <div className="card flex flex-wrap gap-2 p-4">
          {!locked ? (
            <>
              <button className="btn-secondary py-1.5" onClick={() => setEditing(true)}>
                Edit
              </button>
              <button className="btn-secondary py-1.5" disabled={busy} onClick={() => setStatus("completed")}>
                Mark complete
              </button>
              <button className="btn-secondary py-1.5" disabled={busy} onClick={() => setStatus("cancelled")}>
                Cancel goal
              </button>
              <button className="btn-secondary py-1.5 text-red-600" onClick={del}>
                Delete
              </button>
            </>
          ) : (
            <>
              <button className="btn-secondary py-1.5" disabled={busy} onClick={() => setStatus("in_progress")}>
                Reopen goal
              </button>
              <button className="btn-secondary py-1.5 text-red-600" onClick={del}>
                Delete
              </button>
            </>
          )}
        </div>
      )}

      {/* Check-in / comment */}
      {(canEdit || canComment) && !locked && (
        <div className="card space-y-3 p-5">
          <p className="text-sm font-semibold text-slate-700">
            {canEdit ? "Add a check-in" : "Leave a comment"}
          </p>
          {canEdit && (
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={0}
                max={100}
                value={effProgress}
                onChange={(e) => setProgress(Number(e.target.value))}
                className="flex-1"
              />
              <span className="w-12 text-right text-sm font-medium text-slate-600">
                {effProgress}%
              </span>
            </div>
          )}
          <textarea
            className="input"
            rows={3}
            placeholder={canEdit ? "What progress did you make?" : "Your comment…"}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <div className="flex justify-end">
            <button className="btn-primary" disabled={busy} onClick={addCheckin}>
              {canEdit ? "Save check-in" : "Post comment"}
            </button>
          </div>
        </div>
      )}

      {/* History */}
      <div className="card p-5">
        <p className="mb-3 text-sm font-semibold text-slate-700">History</p>
        {goal.checkins.length === 0 ? (
          <p className="text-sm text-slate-400">No check-ins yet.</p>
        ) : (
          <ul className="space-y-3">
            {goal.checkins.map((c) => (
              <li key={c.id} className="border-l-2 border-brand-100 pl-3">
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span className="font-medium text-slate-600">{c.author_name ?? "Someone"}</span>
                  {c.progress !== null && (
                    <span className="rounded bg-brand-50 px-1.5 py-0.5 text-brand-600">
                      {c.progress}%
                    </span>
                  )}
                  <span>{new Date(c.created_at).toLocaleDateString()}</span>
                </div>
                {c.note && <p className="mt-0.5 text-sm text-slate-600">{c.note}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>

      {editing && (
        <GoalFormModal
          goal={goal}
          defaultYear={goal.year}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            reload();
          }}
        />
      )}
    </div>
  );
}
