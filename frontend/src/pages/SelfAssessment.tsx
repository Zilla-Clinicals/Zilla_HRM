import { Link } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ReviewStatusBadge } from "../components/ui";
import { useApi } from "../lib/useApi";
import type { SelfAssignment } from "../shared/types";

export function SelfAssessment() {
  const { data, loading } = useApi<SelfAssignment[]>("/api/self-assessments");

  if (loading) return <LoadingSpinner full />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">My Self-Assessment</h1>
        <p className="text-sm text-slate-500">
          Rate yourself for open review cycles before your manager reviews you
        </p>
      </div>

      {!data || data.length === 0 ? (
        <EmptyState
          title="Nothing to self-assess right now"
          hint="A self-assessment appears here when HR opens a cycle you're part of."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((a) => (
            <Link
              key={a.id}
              to={`/self-assessment/${a.id}`}
              className="card block p-5 hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <p className="font-semibold text-slate-800">
                  {a.cycle_year} · {a.cycle_type.replace("_", " ")}
                </p>
                <ReviewStatusBadge status={a.self_status} />
              </div>
              <p className="mt-3 text-xs text-slate-400">
                {a.self_status === "submitted" ? "Submitted — view only" : "Tap to complete"}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
