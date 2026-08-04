import { Link } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ReviewStatusBadge } from "../components/ui";
import { useApi } from "../lib/useApi";
import type { AssignmentSubject } from "../shared/types";

export function MyReviews() {
  const { data, loading } = useApi<AssignmentSubject[]>("/api/reviews/mine");

  if (loading) return <LoadingSpinner full />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">My Reviews</h1>
        <p className="text-sm text-slate-500">
          People assigned to you in currently open cycles
        </p>
      </div>

      {!data || data.length === 0 ? (
        <EmptyState
          title="Nothing to review right now"
          hint="Assignments appear here when HR opens a cycle."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((a) => (
            <Link key={a.id} to={`/reviews/${a.id}`} className="card block p-5 hover:shadow-md">
              <div className="flex items-center justify-between">
                <p className="font-semibold text-slate-800">{a.subject_name}</p>
                <ReviewStatusBadge status={a.status} />
              </div>
              <p className="mt-1 text-sm text-slate-500">{a.subject_team ?? "—"}</p>
              <p className="mt-3 text-xs text-slate-400">
                {a.cycle_year} · {a.cycle_type.replace("_", " ")}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
