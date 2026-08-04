import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useFeedback } from "../components/feedback";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { KpiStatusBadge, ReviewStatusBadge } from "../components/ui";
import { api, ApiError } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type { AssignmentDetail, Kpi, KpiStatus } from "../shared/types";

interface Draft {
  status: KpiStatus | "";
  comment: string;
  saved: boolean;
}

const STATUS_OPTIONS: { value: KpiStatus; label: string; active: string }[] = [
  { value: "met", label: "Met", active: "bg-emerald-600 text-white border-emerald-600" },
  { value: "partial", label: "Partial", active: "bg-amber-500 text-white border-amber-500" },
  { value: "not_met", label: "Not Met", active: "bg-red-600 text-white border-red-600" },
];

export function DoReview() {
  const { assignmentId } = useParams();
  const navigate = useNavigate();
  const { toast } = useFeedback();
  const { data: assignment, loading, reload } = useApi<AssignmentDetail>(
    assignmentId ? `/api/reviews/${assignmentId}` : null,
  );
  const { data: kpis } = useApi<Kpi[]>("/api/kpis");

  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [summary, setSummary] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const editable = assignment
    ? assignment.cycle_status === "open" && assignment.status !== "submitted"
    : false;

  useEffect(() => {
    if (!assignment || !kpis) return;
    const existing = new Map(assignment.scores.map((s) => [s.kpi_id, s]));
    const next: Record<number, Draft> = {};
    for (const k of kpis) {
      const s = existing.get(k.id);
      next[k.id] = { status: s?.status ?? "", comment: s?.comment ?? "", saved: !!s };
    }
    setDrafts(next);
    setSummary(assignment.summary_comment ?? "");
  }, [assignment, kpis]);

  const progress = useMemo(() => {
    const total = kpis?.length ?? 0;
    const done = Object.values(drafts).filter(
      (d) => d.status !== "" && d.comment.trim() !== "",
    ).length;
    return { done, total };
  }, [drafts, kpis]);

  if (loading) return <LoadingSpinner full />;
  if (!assignment) return <p className="text-sm text-slate-500">Review not found.</p>;

  // A row is savable only with both a status and a comment (comments are required).
  const saveScore = async (kpiId: number) => {
    const d = drafts[kpiId];
    if (!d || d.status === "" || d.comment.trim() === "") return;
    try {
      await api.put(`/api/reviews/${assignment.id}/scores/${kpiId}`, {
        status: d.status,
        comment: d.comment.trim(),
      });
      setDrafts((prev) => ({ ...prev, [kpiId]: { ...prev[kpiId], saved: true } }));
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Could not save");
    }
  };

  const submit = async () => {
    if (progress.done < progress.total) {
      toast("error", "Give every KPI a status and a comment before submitting.");
      return;
    }
    setSubmitting(true);
    try {
      for (const k of kpis ?? []) {
        const d = drafts[k.id];
        if (d && !d.saved) await saveScore(k.id);
      }
      await api.post(`/api/reviews/${assignment.id}/submit`, {
        summary_comment: summary || null,
      });
      toast("success", `Review for ${assignment.subject_name} submitted.`);
      reload();
      navigate("/reviews");
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Could not submit");
    } finally {
      setSubmitting(false);
    }
  };

  const update = (kpiId: number, patch: Partial<Draft>) =>
    setDrafts((prev) => ({ ...prev, [kpiId]: { ...prev[kpiId], ...patch, saved: false } }));

  const selfById = new Map(assignment.self_scores.map((s) => [s.kpi_id, s]));
  const hasSelf = assignment.self_status === "submitted" || assignment.self_scores.length > 0;
  const firstName = assignment.subject_name.split(" ")[0] || "Employee";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/reviews" className="text-sm text-brand-600 hover:underline">
        ← Back to my reviews
      </Link>

      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-800">{assignment.subject_name}</h1>
            <p className="text-sm text-slate-500">
              {assignment.subject_team ?? "—"} · {assignment.cycle_year}{" "}
              {assignment.cycle_type.replace("_", " ")}
            </p>
          </div>
          <ReviewStatusBadge status={assignment.status} />
        </div>
        <p className="mt-3 text-sm text-slate-500">
          {progress.done}/{progress.total} KPIs rated (status + comment required for each)
        </p>
      </div>

      {!editable && (
        <div className="rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-800">
          This review is read-only (
          {assignment.status === "submitted" ? "submitted" : `cycle ${assignment.cycle_status}`}).
        </div>
      )}

      {hasSelf
        ? assignment.self_comment && (
            <div className="rounded-md border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-700">
              <p className="font-medium">
                {assignment.subject_name}'s self-assessment summary
              </p>
              <p className="mt-1 text-slate-600">{assignment.self_comment}</p>
            </div>
          )
        : (
            <div className="rounded-md bg-slate-50 px-4 py-3 text-sm text-slate-500">
              {assignment.subject_name} hasn't submitted a self-assessment yet.
            </div>
          )}

      <div className="space-y-4">
        {(kpis ?? []).map((k) => {
          const d = drafts[k.id] ?? { status: "", comment: "", saved: false };
          const self = selfById.get(k.id);
          const needsComment = d.status !== "" && d.comment.trim() === "";
          return (
            <div key={k.id} className="card p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium text-slate-800">
                    {k.name}{" "}
                    <span className="text-xs font-normal text-slate-400">{k.points} pts</span>
                  </p>
                  <p className="text-xs text-slate-500">{k.category}</p>
                  {k.description && (
                    <p className="mt-1 text-sm text-slate-600">{k.description}</p>
                  )}
                  <div className="mt-1 space-y-0.5 text-xs text-slate-500">
                    {k.measurement && (
                      <p>
                        <span className="font-medium text-slate-400">How it's measured:</span>{" "}
                        {k.measurement}
                      </p>
                    )}
                    {k.target && (
                      <p>
                        <span className="font-medium text-slate-400">Target:</span> {k.target}
                      </p>
                    )}
                  </div>
                </div>
                {self && (
                  <div className="whitespace-nowrap text-right text-xs text-slate-500">
                    <span className="mr-1 text-slate-400">{firstName} rated:</span>
                    <KpiStatusBadge status={self.status} />
                  </div>
                )}
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {STATUS_OPTIONS.map((o) => (
                  <button
                    key={o.value}
                    type="button"
                    disabled={!editable}
                    onClick={() => update(k.id, { status: o.value })}
                    className={`rounded-md border px-3 py-1.5 text-sm ${
                      d.status === o.value
                        ? o.active
                        : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {o.label}
                  </button>
                ))}
                {d.saved && <span className="self-center text-xs text-emerald-600">saved</span>}
              </div>

              {self?.comment && (
                <p className="mt-2 text-xs text-slate-400">
                  {firstName}'s note: {self.comment}
                </p>
              )}

              <textarea
                className={`input mt-3 ${needsComment ? "border-red-300" : ""}`}
                rows={2}
                placeholder="Comment — how did they meet / partially meet / not meet this? (required)"
                disabled={!editable}
                value={d.comment}
                onChange={(e) => update(k.id, { comment: e.target.value })}
                onBlur={() => saveScore(k.id)}
              />
              {needsComment && (
                <p className="mt-1 text-xs text-red-600">A comment is required for this KPI.</p>
              )}
            </div>
          );
        })}
      </div>

      <div className="card p-5">
        <label className="label">Overall summary</label>
        <textarea
          className="input"
          rows={3}
          placeholder="Overall notes for this review…"
          disabled={!editable}
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
        />
      </div>

      {editable && (
        <div className="flex justify-end">
          <button className="btn-primary" onClick={submit} disabled={submitting}>
            {submitting ? "Submitting…" : "Submit review"}
          </button>
        </div>
      )}
    </div>
  );
}
