import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { CycleStatusBadge, ErrorText, Modal } from "../components/ui";
import { api } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type { AssignedSurvey, Survey } from "../shared/types";

export function Surveys() {
  const { can } = useAuth();
  const canCreate = can("create_surveys");
  const { data: assigned, loading } = useApi<AssignedSurvey[]>("/api/surveys/assigned");
  const {
    data: managed,
    reload: reloadManaged,
  } = useApi<Survey[]>(canCreate ? "/api/surveys" : null);
  const [creating, setCreating] = useState(false);

  if (loading) return <LoadingSpinner full />;

  const todo = (assigned ?? []).filter((s) => !s.completed);
  const done = (assigned ?? []).filter((s) => s.completed);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Surveys</h1>
          <p className="text-sm text-slate-500">Forms assigned to you, and surveys you run</p>
        </div>
        {canCreate && (
          <button className="btn-primary" onClick={() => setCreating(true)}>
            + New survey
          </button>
        )}
      </div>

      {/* Assigned to me */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-700">Assigned to me</h2>
        {todo.length === 0 && done.length === 0 ? (
          <EmptyState title="Nothing to fill out" hint="Surveys assigned to you show up here." />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {todo.map((s) => (
              <Link key={s.id} to={`/surveys/${s.id}/fill`} className="card block p-5 hover:shadow-md">
                <div className="flex items-center justify-between">
                  <p className="font-semibold text-slate-800">{s.title}</p>
                  {s.anonymous && (
                    <span className="badge bg-slate-100 text-slate-500">Anonymous</span>
                  )}
                </div>
                {s.description && (
                  <p className="mt-1 line-clamp-2 text-sm text-slate-500">{s.description}</p>
                )}
                <p className="mt-3 text-xs font-medium text-brand-600">Tap to respond →</p>
              </Link>
            ))}
            {done.map((s) => (
              <div key={s.id} className="card p-5 opacity-70">
                <div className="flex items-center justify-between">
                  <p className="font-semibold text-slate-800">{s.title}</p>
                  <span className="badge bg-emerald-100 text-emerald-700">Completed</span>
                </div>
                <p className="mt-3 text-xs text-slate-400">Thanks for responding</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Surveys I manage */}
      {canCreate && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-700">Surveys I manage</h2>
          {!managed || managed.length === 0 ? (
            <EmptyState
              title="No surveys yet"
              hint="Create a survey, add questions, assign recipients, then open it."
            />
          ) : (
            <div className="card overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="th">Survey</th>
                    <th className="th">Status</th>
                    <th className="th">Questions</th>
                    <th className="th">Responses</th>
                    <th className="th"></th>
                  </tr>
                </thead>
                <tbody>
                  {managed.map((s) => (
                    <tr key={s.id} className="border-t border-slate-100">
                      <td className="td font-medium">
                        {s.title}
                        {s.anonymous && (
                          <span className="ml-2 badge bg-slate-100 text-slate-500">Anon</span>
                        )}
                      </td>
                      <td className="td">
                        <CycleStatusBadge status={s.status} />
                      </td>
                      <td className="td">{s.question_count}</td>
                      <td className="td">
                        {s.response_count}/{s.assigned_count}
                      </td>
                      <td className="td text-right">
                        <Link
                          to={`/surveys/${s.id}/manage`}
                          className="text-brand-600 hover:underline"
                        >
                          Manage
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {creating && (
        <CreateSurveyModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            reloadManaged();
          }}
        />
      )}
    </div>
  );
}

function CreateSurveyModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (id: number) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [anonymous, setAnonymous] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = await api.post<Survey>("/api/surveys", {
        title,
        description: description || null,
        anonymous,
      });
      onCreated(s.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create survey");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="New survey" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">Title</label>
          <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required />
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
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={anonymous}
            onChange={(e) => setAnonymous(e.target.checked)}
          />
          Anonymous — responses won't be linked to individuals
        </label>
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
