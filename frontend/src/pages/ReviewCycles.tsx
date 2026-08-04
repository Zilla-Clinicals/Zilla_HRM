import { useState } from "react";
import { EmptyState } from "../components/EmptyState";
import { useFeedback } from "../components/feedback";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { CycleStatusBadge, ErrorText, Modal } from "../components/ui";
import { api, ApiError } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type { AssignmentAdmin, Cycle, CycleType, Employee } from "../shared/types";

export function ReviewCycles() {
  const { toast, confirm } = useFeedback();
  const { data: cycles, loading, reload } = useApi<Cycle[]>("/api/cycles");
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [manageCycle, setManageCycle] = useState<Cycle | null>(null);

  if (loading) return <LoadingSpinner full />;

  const act = async (c: Cycle, action: "assign" | "open" | "close") => {
    if (action === "close") {
      const ok = await confirm({
        title: `Close ${c.year} ${c.type.replace("_", " ")}?`,
        message: "All scores become read-only. This can't be undone.",
        confirmLabel: "Close cycle",
        danger: true,
      });
      if (!ok) return;
    }
    setBusyId(c.id);
    try {
      if (action === "assign") {
        const res = await api.post<unknown[]>(`/api/cycles/${c.id}/assign`, {
          skip_without_manager: true,
        });
        toast("success", `Assigned ${res.length} reviewer(s) for ${c.year} ${c.type.replace("_", " ")}.`);
      } else {
        await api.post(`/api/cycles/${c.id}/${action}`);
        toast("success", `Cycle ${action === "open" ? "opened" : "closed"}.`);
      }
      reload();
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">Review Cycles</h1>
        <button className="btn-primary" onClick={() => setCreating(true)}>
          + New cycle
        </button>
      </div>

      {!cycles || cycles.length === 0 ? (
        <EmptyState
          title="No review cycles"
          hint="Create a draft cycle, assign reviewers, then open it."
        />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[720px]">
            <thead className="bg-slate-50">
              <tr>
                <th className="th">Cycle</th>
                <th className="th">Status</th>
                <th className="th">Window</th>
                <th className="th text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {cycles.map((c) => (
                <tr key={c.id} className="border-t border-slate-100">
                  <td className="td font-medium">
                    {c.year} · {c.type.replace("_", " ")}
                  </td>
                  <td className="td">
                    <CycleStatusBadge status={c.status} />
                  </td>
                  <td className="td text-slate-500">
                    {new Date(c.opens_at).toLocaleDateString()} –{" "}
                    {new Date(c.closes_at).toLocaleDateString()}
                  </td>
                  <td className="td">
                    <div className="flex justify-end gap-2">
                      {c.status === "draft" && (
                        <>
                          <button
                            className="btn-secondary"
                            disabled={busyId === c.id}
                            onClick={() => act(c, "assign")}
                          >
                            Assign
                          </button>
                          <button
                            className="btn-secondary"
                            disabled={busyId === c.id}
                            onClick={() => setManageCycle(c)}
                          >
                            Reviewers
                          </button>
                          <button
                            className="btn-primary"
                            disabled={busyId === c.id}
                            onClick={() => act(c, "open")}
                          >
                            Open
                          </button>
                        </>
                      )}
                      {c.status === "open" && (
                        <button
                          className="btn-danger"
                          disabled={busyId === c.id}
                          onClick={() => act(c, "close")}
                        >
                          Close
                        </button>
                      )}
                      {c.status === "closed" && (
                        <span className="text-sm text-slate-400">Read-only</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {creating && (
        <CreateCycleModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            reload();
          }}
        />
      )}

      {manageCycle && (
        <ManageReviewersModal cycle={manageCycle} onClose={() => setManageCycle(null)} />
      )}
    </div>
  );
}

function ManageReviewersModal({ cycle, onClose }: { cycle: Cycle; onClose: () => void }) {
  const { toast } = useFeedback();
  const {
    data: assignments,
    loading,
    reload,
  } = useApi<AssignmentAdmin[]>(`/api/cycles/${cycle.id}/assignments`);
  const { data: employees } = useApi<Employee[]>("/api/employees");
  const [savingId, setSavingId] = useState<number | null>(null);

  const changeReviewer = async (a: AssignmentAdmin, reviewerId: number) => {
    setSavingId(a.id);
    try {
      await api.patch(`/api/cycles/${cycle.id}/assignments/${a.id}`, {
        reviewer_employee_id: reviewerId,
      });
      toast("success", `Reviewer updated for ${a.subject_name}.`);
      reload();
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Could not update reviewer");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <Modal title={`Reviewers · ${cycle.year} ${cycle.type.replace("_", " ")}`} onClose={onClose}>
      {loading ? (
        <LoadingSpinner />
      ) : !assignments || assignments.length === 0 ? (
        <p className="text-sm text-slate-500">
          No assignments yet — click <span className="font-medium">Assign</span> first.
        </p>
      ) : (
        <div className="max-h-[26rem] space-y-3 overflow-y-auto">
          {assignments.map((a) => (
            <div key={a.id} className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-800">{a.subject_name}</p>
                <p className="text-xs text-slate-400">reviewed by</p>
              </div>
              <select
                className="input max-w-[12rem]"
                disabled={savingId === a.id}
                value={a.reviewer_employee_id}
                onChange={(e) => changeReviewer(a, Number(e.target.value))}
              >
                {(employees ?? [])
                  .filter((e) => e.id !== a.subject_employee_id)
                  .map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.full_name}
                    </option>
                  ))}
              </select>
            </div>
          ))}
        </div>
      )}
      <div className="mt-5 flex justify-end">
        <button className="btn-primary" onClick={onClose}>
          Done
        </button>
      </div>
    </Modal>
  );
}

function CreateCycleModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [type, setType] = useState<CycleType>("mid_year");
  const [opensAt, setOpensAt] = useState("");
  const [closesAt, setClosesAt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/cycles", {
        year,
        type,
        opens_at: new Date(opensAt).toISOString(),
        closes_at: new Date(closesAt).toISOString(),
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create cycle");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="New review cycle" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Year</label>
            <input
              type="number"
              className="input"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              required
            />
          </div>
          <div>
            <label className="label">Type</label>
            <select
              className="input"
              value={type}
              onChange={(e) => setType(e.target.value as CycleType)}
            >
              <option value="mid_year">Mid year</option>
              <option value="end_year">End year</option>
            </select>
          </div>
        </div>
        <div>
          <label className="label">Opens at</label>
          <input
            type="datetime-local"
            className="input"
            value={opensAt}
            onChange={(e) => setOpensAt(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="label">Closes at</label>
          <input
            type="datetime-local"
            className="input"
            value={closesAt}
            onChange={(e) => setClosesAt(e.target.value)}
            required
          />
        </div>
        <ErrorText message={error} />
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Creating…" : "Create draft"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
