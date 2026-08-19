import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "./EmptyState";
import { LoadingSpinner } from "./LoadingSpinner";
import { ErrorText, GoalStatusBadge, Modal } from "./ui";
import { api } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type { Goal, GoalCategory, GoalDetail } from "../shared/types";

export const CATEGORY_LABELS: Record<GoalCategory, string> = {
  performance: "Performance",
  development: "Development",
  business: "Business",
  other: "Other",
};

export const CATEGORY_ACCENT: Record<GoalCategory, string> = {
  performance: "from-brand-600 to-brand-400",
  development: "from-emerald-500 to-teal-500",
  business: "from-amber-500 to-orange-500",
  other: "from-slate-400 to-slate-500",
};

export function ProgressBar({ value, muted }: { value: number; muted?: boolean }) {
  return (
    <div className="h-2 w-full rounded-full bg-slate-100">
      <div
        className={`h-2 rounded-full ${muted ? "bg-slate-300" : "bg-brand-500"}`}
        style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
      />
    </div>
  );
}

/**
 * Self-contained goals panel. Powers both "My Goals" (mine) and the profile
 * section (a specific employee). `canEdit` = the viewer owns these goals;
 * `canComment` = a manager/HR viewer who may leave a comment.
 */
export function GoalsPanel({
  mine = false,
  employeeId,
  canEdit,
  heading,
}: {
  mine?: boolean;
  employeeId?: number;
  canEdit: boolean;
  heading?: string;
}) {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const base = mine ? "/api/goals/mine" : `/api/employees/${employeeId}/goals`;
  const { data, loading, error, reload } = useApi<Goal[]>(`${base}?year=${year}`);
  const [creating, setCreating] = useState(false);

  // Managers/HR may be forbidden from another employee's goals — hide silently.
  if (error && !mine) return null;

  const years = useMemo(() => {
    const set = new Set<number>([currentYear, currentYear - 1]);
    (data ?? []).forEach((g) => set.add(g.year));
    return [...set].sort((a, b) => b - a);
  }, [data, currentYear]);

  const goals = data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-slate-700">{heading ?? "Goals"}</h2>
        <div className="flex items-center gap-2">
          <select
            className="input max-w-[7rem] py-1.5"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          {canEdit && (
            <button className="btn-primary py-1.5" onClick={() => setCreating(true)}>
              + New goal
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : goals.length === 0 ? (
        <EmptyState
          title={`No goals for ${year}`}
          hint={canEdit ? "Set a goal for the year and track it with check-ins." : undefined}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {goals.map((g) => (
            <Link
              key={g.id}
              to={`/goals/${g.id}`}
              className="card card-interactive relative block overflow-hidden p-5 text-left"
            >
              <div
                className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${CATEGORY_ACCENT[g.category]}`}
              />
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-slate-800">{g.title}</p>
                  <p className="text-xs text-slate-400">
                    {CATEGORY_LABELS[g.category]}
                    {g.target_date ? ` · due ${g.target_date}` : ""}
                  </p>
                </div>
                <GoalStatusBadge status={g.status} />
              </div>
              <div className="mt-3 flex items-center gap-3">
                <ProgressBar value={g.progress} muted={g.status === "cancelled"} />
                <span className="w-10 text-right text-sm font-medium text-slate-600">
                  {g.progress}%
                </span>
              </div>
              {g.checkin_count > 0 && (
                <p className="mt-2 text-xs text-slate-400">
                  {g.checkin_count} check-in{g.checkin_count === 1 ? "" : "s"}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}

      {creating && (
        <GoalFormModal
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            reload();
          }}
          defaultYear={year}
        />
      )}
    </div>
  );
}

export function GoalFormModal({
  onClose,
  onSaved,
  defaultYear,
  goal,
}: {
  onClose: () => void;
  onSaved: () => void;
  defaultYear: number;
  goal?: GoalDetail;
}) {
  const [title, setTitle] = useState(goal?.title ?? "");
  const [description, setDescription] = useState(goal?.description ?? "");
  const [category, setCategory] = useState<GoalCategory>(goal?.category ?? "performance");
  const [targetDate, setTargetDate] = useState(goal?.target_date ?? "");
  const [year, setYear] = useState(goal?.year ?? defaultYear);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = {
        year,
        title,
        description: description || null,
        category,
        target_date: targetDate || null,
      };
      if (goal) await api.patch(`/api/goals/${goal.id}`, body);
      else await api.post("/api/goals", body);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save goal");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={goal ? "Edit goal" : "New goal"} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">Goal</label>
          <input
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Complete AWS certification"
            required
          />
        </div>
        <div>
          <label className="label">Description</label>
          <textarea
            className="input"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="label">Category</label>
            <select
              className="input"
              value={category}
              onChange={(e) => setCategory(e.target.value as GoalCategory)}
            >
              {Object.entries(CATEGORY_LABELS).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Year</label>
            <input
              type="number"
              className="input"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            />
          </div>
          <div>
            <label className="label">Target date</label>
            <input
              type="date"
              className="input"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
            />
          </div>
        </div>
        <ErrorText message={error} />
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
