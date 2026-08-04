import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useFeedback } from "../components/feedback";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { api, ApiError } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type { SurveyFill, SurveyQuestion } from "../shared/types";

type AnswerMap = Record<number, unknown>;

function isEmpty(v: unknown): boolean {
  return v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);
}

export function DoSurvey() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useFeedback();
  const { data: survey, loading } = useApi<SurveyFill>(id ? `/api/surveys/${id}/fill` : null);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [submitting, setSubmitting] = useState(false);

  if (loading) return <LoadingSpinner full />;
  if (!survey) return <p className="text-sm text-slate-500">Survey not available.</p>;

  if (survey.completed) {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="card p-8 text-center">
          <p className="text-2xl">✓</p>
          <h1 className="mt-2 text-lg font-semibold text-slate-800">
            You've completed "{survey.title}"
          </h1>
          <p className="mt-1 text-sm text-slate-500">Thanks for your response.</p>
          <Link to="/surveys" className="btn-primary mt-4 inline-flex">
            Back to surveys
          </Link>
        </div>
      </div>
    );
  }

  const set = (qid: number, value: unknown) => setAnswers((a) => ({ ...a, [qid]: value }));

  const submit = async () => {
    const missing = survey.questions.find((q) => q.required && isEmpty(answers[q.id]));
    if (missing) {
      toast("error", `"${missing.prompt}" is required.`);
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/api/surveys/${survey.id}/respond`, {
        answers: survey.questions
          .filter((q) => !isEmpty(answers[q.id]))
          .map((q) => ({ question_id: q.id, value: answers[q.id] })),
      });
      toast("success", "Response submitted. Thank you!");
      navigate("/surveys");
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Could not submit");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link to="/surveys" className="text-sm text-brand-600 hover:underline">
        ← Back to surveys
      </Link>

      <div className="card p-6">
        <h1 className="text-xl font-semibold text-slate-800">{survey.title}</h1>
        {survey.description && <p className="mt-1 text-sm text-slate-500">{survey.description}</p>}
        {survey.anonymous && (
          <p className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
            🔒 This survey is anonymous — your answers won't be linked to you.
          </p>
        )}
      </div>

      <div className="space-y-4">
        {survey.questions.map((q, i) => (
          <div key={q.id} className="card p-5">
            <p className="font-medium text-slate-800">
              {i + 1}. {q.prompt}
              {q.required && <span className="ml-1 text-red-500">*</span>}
            </p>
            <div className="mt-3">
              <QuestionInput q={q} value={answers[q.id]} onChange={(v) => set(q.id, v)} />
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-end">
        <button className="btn-primary" onClick={submit} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit response"}
        </button>
      </div>
    </div>
  );
}

function QuestionInput({
  q,
  value,
  onChange,
}: {
  q: SurveyQuestion;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  switch (q.type) {
    case "short_text":
      return (
        <input className="input" value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} />
      );
    case "long_text":
      return (
        <textarea
          className="input"
          rows={3}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
        />
      );
    case "date":
      return (
        <input
          type="date"
          className="input max-w-xs"
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
        />
      );
    case "dropdown":
      return (
        <select className="input" value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)}>
          <option value="">— select —</option>
          {(q.choices ?? []).map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      );
    case "single_choice":
      return (
        <div className="space-y-2">
          {(q.choices ?? []).map((c) => (
            <label key={c} className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="radio"
                name={`q${q.id}`}
                checked={value === c}
                onChange={() => onChange(c)}
              />
              {c}
            </label>
          ))}
        </div>
      );
    case "multi_choice": {
      const arr = (value as string[]) ?? [];
      const toggle = (c: string) =>
        onChange(arr.includes(c) ? arr.filter((x) => x !== c) : [...arr, c]);
      return (
        <div className="space-y-2">
          {(q.choices ?? []).map((c) => (
            <label key={c} className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={arr.includes(c)} onChange={() => toggle(c)} />
              {c}
            </label>
          ))}
        </div>
      );
    }
    case "yes_no":
      return (
        <div className="flex gap-2">
          {["yes", "no"].map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => onChange(v)}
              className={`rounded-md border px-4 py-1.5 text-sm capitalize ${
                value === v
                  ? "border-brand-500 bg-brand-600 text-white"
                  : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      );
    case "rating": {
      const max = q.scale_max ?? 5;
      return (
        <div className="flex gap-1.5">
          {Array.from({ length: max }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => onChange(n)}
              className={`grid h-9 w-9 place-items-center rounded-lg border text-sm font-medium ${
                (value as number) >= n
                  ? "border-amber-400 bg-amber-400 text-white"
                  : "border-slate-300 bg-white text-slate-500 hover:bg-slate-50"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      );
    }
    default:
      return null;
  }
}
