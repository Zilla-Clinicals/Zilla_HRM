import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { EmptyState } from "../components/EmptyState";
import { useFeedback } from "../components/feedback";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { CycleStatusBadge, ErrorText, Modal } from "../components/ui";
import { api } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type {
  Employee,
  SurveyAssignmentStatus,
  SurveyDetail,
  SurveyQuestion,
  SurveyQuestionType,
  SurveyResults,
} from "../shared/types";

const TYPE_LABELS: Record<SurveyQuestionType, string> = {
  short_text: "Short text",
  long_text: "Paragraph",
  single_choice: "Single choice",
  multi_choice: "Checkboxes",
  dropdown: "Dropdown",
  rating: "Rating",
  yes_no: "Yes / No",
  date: "Date",
};

const CHOICE_TYPES: SurveyQuestionType[] = ["single_choice", "multi_choice", "dropdown"];

type Tab = "build" | "recipients" | "results";

export function SurveyManage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast, confirm } = useFeedback();
  const { data: survey, loading, reload } = useApi<SurveyDetail>(
    id ? `/api/surveys/${id}` : null,
  );
  const [tab, setTab] = useState<Tab>("build");

  if (loading) return <LoadingSpinner full />;
  if (!survey) return <p className="text-sm text-slate-500">Survey not found.</p>;

  const isDraft = survey.status === "draft";

  const act = async (action: "open" | "close") => {
    try {
      await api.post(`/api/surveys/${survey.id}/${action}`);
      toast("success", action === "open" ? "Survey opened." : "Survey closed.");
      reload();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Action failed");
    }
  };

  const remove = async () => {
    if (!(await confirm({ title: `Delete "${survey.title}"?`, confirmLabel: "Delete", danger: true })))
      return;
    await api.del(`/api/surveys/${survey.id}`);
    toast("success", "Survey deleted.");
    navigate("/surveys");
  };

  return (
    <div className="space-y-6">
      <Link to="/surveys" className="text-sm text-brand-600 hover:underline">
        ← Back to surveys
      </Link>

      <div className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-800">{survey.title}</h1>
              <CycleStatusBadge status={survey.status} />
              {survey.anonymous && (
                <span className="badge bg-slate-100 text-slate-500">Anonymous</span>
              )}
            </div>
            {survey.description && (
              <p className="mt-1 text-sm text-slate-500">{survey.description}</p>
            )}
            <p className="mt-1 text-xs text-slate-400">
              {survey.question_count} questions · {survey.response_count}/{survey.assigned_count}{" "}
              responded
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isDraft && (
              <button className="btn-primary" onClick={() => act("open")}>
                Open survey
              </button>
            )}
            {survey.status === "open" && (
              <button className="btn-danger" onClick={() => act("close")}>
                Close survey
              </button>
            )}
            <button className="btn-secondary" onClick={remove}>
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200">
        {(["build", "recipients", "results"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium capitalize transition ${
              tab === t
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "build" && <BuildTab survey={survey} isDraft={isDraft} onChanged={reload} />}
      {tab === "recipients" && <RecipientsTab survey={survey} onChanged={reload} />}
      {tab === "results" && <ResultsTab surveyId={survey.id} />}
    </div>
  );
}

// ---------------------------------------------------------------- Build tab
function BuildTab({
  survey,
  isDraft,
  onChanged,
}: {
  survey: SurveyDetail;
  isDraft: boolean;
  onChanged: () => void;
}) {
  const { toast, confirm } = useFeedback();
  const [editing, setEditing] = useState<SurveyQuestion | "new" | null>(null);

  const removeQ = async (q: SurveyQuestion) => {
    if (!(await confirm({ title: "Delete this question?", confirmLabel: "Delete", danger: true })))
      return;
    await api.del(`/api/surveys/${survey.id}/questions/${q.id}`);
    toast("success", "Question removed.");
    onChanged();
  };

  return (
    <div className="space-y-4">
      {!isDraft && (
        <div className="rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-800">
          The survey is {survey.status} — questions are locked.
        </div>
      )}

      {survey.questions.length === 0 ? (
        <EmptyState title="No questions yet" hint="Add your first question below." />
      ) : (
        <div className="space-y-3">
          {survey.questions.map((q, i) => (
            <div key={q.id} className="card p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-800">
                    {i + 1}. {q.prompt}
                    {q.required && <span className="ml-1 text-red-500">*</span>}
                  </p>
                  <p className="text-xs text-slate-400">
                    {TYPE_LABELS[q.type]}
                    {q.choices ? ` · ${q.choices.join(", ")}` : ""}
                    {q.scale_max ? ` · 1–${q.scale_max}` : ""}
                  </p>
                </div>
                {isDraft && (
                  <div className="flex gap-2 text-sm">
                    <button className="text-brand-600 hover:underline" onClick={() => setEditing(q)}>
                      Edit
                    </button>
                    <button className="text-red-600 hover:underline" onClick={() => removeQ(q)}>
                      Delete
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {isDraft && (
        <button className="btn-secondary" onClick={() => setEditing("new")}>
          + Add question
        </button>
      )}

      {editing && (
        <QuestionModal
          surveyId={survey.id}
          question={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            onChanged();
          }}
        />
      )}
    </div>
  );
}

function QuestionModal({
  surveyId,
  question,
  onClose,
  onSaved,
}: {
  surveyId: number;
  question: SurveyQuestion | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [type, setType] = useState<SurveyQuestionType>(question?.type ?? "short_text");
  const [prompt, setPrompt] = useState(question?.prompt ?? "");
  const [required, setRequired] = useState(question?.required ?? false);
  const [choices, setChoices] = useState<string[]>(question?.choices ?? ["", ""]);
  const [scaleMax, setScaleMax] = useState(question?.scale_max ?? 5);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isChoice = CHOICE_TYPES.includes(type);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = {
        type,
        prompt,
        required,
        choices: isChoice ? choices.map((c) => c.trim()).filter(Boolean) : null,
        scale_max: type === "rating" ? scaleMax : null,
      };
      if (question) await api.patch(`/api/surveys/${surveyId}/questions/${question.id}`, body);
      else await api.post(`/api/surveys/${surveyId}/questions`, body);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save question");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={question ? "Edit question" : "Add question"} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">Question type</label>
          <select
            className="input"
            value={type}
            onChange={(e) => setType(e.target.value as SurveyQuestionType)}
          >
            {Object.entries(TYPE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Prompt</label>
          <input className="input" value={prompt} onChange={(e) => setPrompt(e.target.value)} required />
        </div>

        {isChoice && (
          <div>
            <label className="label">Options</label>
            <div className="space-y-2">
              {choices.map((c, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    className="input"
                    value={c}
                    onChange={(e) =>
                      setChoices((cs) => cs.map((x, j) => (j === i ? e.target.value : x)))
                    }
                    placeholder={`Option ${i + 1}`}
                  />
                  {choices.length > 2 && (
                    <button
                      type="button"
                      className="btn-secondary px-3"
                      onClick={() => setChoices((cs) => cs.filter((_, j) => j !== i))}
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button
              type="button"
              className="mt-2 text-sm text-brand-600 hover:underline"
              onClick={() => setChoices((cs) => [...cs, ""])}
            >
              + Add option
            </button>
          </div>
        )}

        {type === "rating" && (
          <div>
            <label className="label">Scale max</label>
            <input
              type="number"
              min={2}
              max={10}
              className="input max-w-[6rem]"
              value={scaleMax}
              onChange={(e) => setScaleMax(Number(e.target.value))}
            />
          </div>
        )}

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={required} onChange={(e) => setRequired(e.target.checked)} />
          Required
        </label>

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

// ------------------------------------------------------------ Recipients tab
function RecipientsTab({ survey, onChanged }: { survey: SurveyDetail; onChanged: () => void }) {
  const { can } = useAuth();
  const { toast } = useFeedback();
  const { data: assignments, reload } = useApi<SurveyAssignmentStatus[]>(
    `/api/surveys/${survey.id}/assignments`,
  );
  const { data: employees } = useApi<Employee[]>("/api/employees");
  const [scope, setScope] = useState<"everyone" | "specific">("everyone");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const isDraft = survey.status === "draft";

  const assign = async () => {
    setBusy(true);
    try {
      const body =
        scope === "everyone"
          ? { scope: can("manage_surveys") ? "all" : "team", employee_ids: [] }
          : { scope: "employees", employee_ids: [...selected] };
      const s = await api.post<SurveyDetail>(`/api/surveys/${survey.id}/assign`, body);
      toast("success", `Assigned — ${s.assigned_count} recipient(s) total.`);
      setSelected(new Set());
      reload();
      onChanged();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not assign");
    } finally {
      setBusy(false);
    }
  };

  const responded = (assignments ?? []).filter((a) => a.completed).length;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {isDraft && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-700">Assign recipients</h3>
          <div className="mt-3 space-y-2 text-sm">
            <label className="flex items-center gap-2">
              <input type="radio" checked={scope === "everyone"} onChange={() => setScope("everyone")} />
              {can("manage_surveys") ? "Everyone" : "My whole team"}
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" checked={scope === "specific"} onChange={() => setScope("specific")} />
              Specific people
            </label>
          </div>

          {scope === "specific" && (
            <div className="mt-3 max-h-64 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
              {(employees ?? []).map((e) => (
                <label key={e.id} className="flex items-center gap-2 px-1 py-1 text-sm">
                  <input
                    type="checkbox"
                    checked={selected.has(e.id)}
                    onChange={() =>
                      setSelected((s) => {
                        const n = new Set(s);
                        n.has(e.id) ? n.delete(e.id) : n.add(e.id);
                        return n;
                      })
                    }
                  />
                  {e.full_name}
                  <span className="text-xs text-slate-400">{e.team ?? ""}</span>
                </label>
              ))}
            </div>
          )}

          <button
            className="btn-primary mt-4"
            disabled={busy || (scope === "specific" && selected.size === 0)}
            onClick={assign}
          >
            {busy ? "Assigning…" : "Assign"}
          </button>
        </div>
      )}

      <div className="card p-5">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">Recipients</h3>
          <span className="text-sm text-slate-500">
            {responded}/{assignments?.length ?? 0} responded
          </span>
        </div>
        {!assignments || assignments.length === 0 ? (
          <p className="text-sm text-slate-400">No recipients assigned yet.</p>
        ) : (
          <ul className="max-h-80 space-y-1 overflow-y-auto">
            {assignments.map((a) => (
              <li
                key={a.employee_id}
                className="flex items-center justify-between border-b border-slate-100 py-1.5 text-sm"
              >
                <span className="text-slate-700">{a.name}</span>
                {a.completed ? (
                  <span className="badge bg-emerald-100 text-emerald-700">Responded</span>
                ) : (
                  <span className="badge bg-slate-100 text-slate-500">Pending</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// --------------------------------------------------------------- Results tab
function ResultsTab({ surveyId }: { surveyId: number }) {
  const { data, loading } = useApi<SurveyResults>(`/api/surveys/${surveyId}/results`);
  if (loading) return <LoadingSpinner />;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <p className="text-sm text-slate-600">
          <span className="text-2xl font-bold text-slate-800">{data.response_count}</span>
          <span className="text-slate-400"> / {data.assigned_count} responded</span>
          {data.anonymous && (
            <span className="ml-3 badge bg-slate-100 text-slate-500">Anonymous</span>
          )}
        </p>
      </div>

      {data.questions.map((q) => (
        <div key={q.question_id} className="card p-5">
          <p className="font-medium text-slate-800">{q.prompt}</p>
          <p className="text-xs text-slate-400">{q.total_answers} answers</p>

          {q.counts && (
            <div className="mt-3 space-y-2">
              {q.counts.map((c) => {
                const total = q.counts!.reduce((s, x) => s + x.count, 0) || 1;
                const pct = Math.round((c.count / total) * 100);
                return (
                  <div key={c.label}>
                    <div className="mb-0.5 flex justify-between text-xs text-slate-600">
                      <span>{c.label}</span>
                      <span>
                        {c.count} · {pct}%
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-100">
                      <div className="h-2 rounded-full bg-brand-500" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
              {q.average !== null && (
                <p className="pt-1 text-sm font-medium text-slate-600">
                  Average: {q.average}
                </p>
              )}
            </div>
          )}

          {q.texts && (
            <div className="mt-3 space-y-2">
              {q.texts.length === 0 ? (
                <p className="text-sm text-slate-400">No answers.</p>
              ) : (
                q.texts.map((t, i) => (
                  <p key={i} className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">
                    {t}
                  </p>
                ))
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
