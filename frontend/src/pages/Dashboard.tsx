import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { ScoreDistribution } from "../components/charts/ScoreDistribution";
import { EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ReviewStatusBadge } from "../components/ui";
import { api } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type {
  Breakdown,
  Cycle,
  CycleDashboard,
  OrgOverview,
  ReviewHistoryItem,
} from "../shared/types";

function StatTile({
  label,
  value,
  accent = "from-brand-500 to-accent-500",
  icon = "•",
}: {
  label: string;
  value: string;
  accent?: string;
  icon?: string;
}) {
  return (
    <div className="card card-interactive relative overflow-hidden p-4">
      <div
        className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${accent}`}
        aria-hidden
      />
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
        <span
          className={`grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br ${accent} text-sm text-white shadow-glow-sm`}
        >
          {icon}
        </span>
      </div>
      <p className="mt-2 text-3xl font-bold tracking-tight text-slate-800">{value}</p>
    </div>
  );
}

function HrDashboard() {
  const { data: cycles, loading } = useApi<Cycle[]>("/api/cycles");
  const { data: org } = useApi<OrgOverview>("/api/dashboard/overview");
  const [cycleId, setCycleId] = useState<number | null>(null);
  const [dash, setDash] = useState<CycleDashboard | null>(null);

  useEffect(() => {
    if (cycles && cycles.length && cycleId === null) setCycleId(cycles[0].id);
  }, [cycles, cycleId]);

  useEffect(() => {
    if (cycleId === null) return;
    api.get<CycleDashboard>(`/api/dashboard/cycle/${cycleId}`).then(setDash);
  }, [cycleId]);

  if (loading) return <LoadingSpinner full />;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-800">Dashboard</h1>

      {org && <OrgOverviewSection org={org} />}

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <h2 className="text-base font-semibold text-slate-800">Performance reviews</h2>
        {cycles && cycles.length > 0 && (
          <select
            className="input max-w-xs"
            value={cycleId ?? ""}
            onChange={(e) => setCycleId(Number(e.target.value))}
          >
            {cycles.map((c) => (
              <option key={c.id} value={c.id}>
                {c.year} · {c.type.replace("_", " ")} ({c.status})
              </option>
            ))}
          </select>
        )}
      </div>

      {!cycles || cycles.length === 0 ? (
        <EmptyState
          title="No review cycles yet"
          hint="Create your first cycle to start tracking performance."
          action={
            <Link to="/cycles" className="btn-primary">
              Go to Review Cycles
            </Link>
          }
        />
      ) : (
        dash && (
          <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatTile
              label="Completion"
              value={`${Math.round(dash.completion_rate * 100)}%`}
              accent="from-emerald-500 to-teal-500"
              icon="✓"
            />
            <StatTile
              label="Submitted"
              value={`${dash.submitted_assignments}/${dash.total_assignments}`}
              accent="from-brand-600 to-brand-400"
              icon="✎"
            />
            <StatTile
              label="Average score"
              value={dash.average_score !== null ? `${dash.average_score.toFixed(1)}/100` : "—"}
              accent="from-accent-500 to-accent-400"
              icon="★"
            />
            <StatTile
              label="Teams"
              value={String(dash.team_averages.length)}
              accent="from-amber-500 to-orange-500"
              icon="◍"
            />
          </div>

          <div className="card p-5">
            <h2 className="mb-3 text-sm font-semibold text-slate-700">
              Category performance (avg points earned / max)
            </h2>
            {dash.category_rollup.every((c) => c.earned_avg === 0) ? (
              <p className="text-sm text-slate-500">No scored reviews yet.</p>
            ) : (
              <div className="space-y-3">
                {dash.category_rollup.map((c) => {
                  const pct = c.max_points ? (c.earned_avg / c.max_points) * 100 : 0;
                  return (
                    <div key={c.category}>
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className="text-slate-700">{c.category}</span>
                        <span className="text-slate-500">
                          {c.earned_avg.toFixed(1)}/{c.max_points} · {c.status_band}
                        </span>
                      </div>
                      <div className="h-2.5 w-full rounded-full bg-slate-100">
                        <div
                          className={`h-2.5 rounded-full ${
                            pct >= 85
                              ? "bg-emerald-500"
                              : pct >= 60
                                ? "bg-amber-500"
                                : "bg-red-500"
                          }`}
                          style={{ width: `${Math.min(pct, 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="card p-5">
              <h2 className="mb-3 text-sm font-semibold text-slate-700">
                Rating distribution
              </h2>
              <ScoreDistribution data={dash.status_distribution} />
            </div>
            <div className="card p-5">
              <h2 className="mb-3 text-sm font-semibold text-slate-700">
                Team averages (/100)
              </h2>
              {dash.team_averages.length === 0 ? (
                <p className="text-sm text-slate-500">No scored reviews yet.</p>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="th">Team</th>
                      <th className="th">Avg</th>
                      <th className="th">Reviews</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dash.team_averages.map((t) => (
                      <tr key={t.team} className="border-b border-slate-100">
                        <td className="td">{t.team}</td>
                        <td className="td font-medium">{t.average_score.toFixed(1)}</td>
                        <td className="td">{t.subject_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
          </>
        )
      )}
    </div>
  );
}

function OrgOverviewSection({ org }: { org: OrgOverview }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Active" value={String(org.active_employees)} accent="from-emerald-500 to-teal-500" icon="●" />
        <StatTile label="Employees" value={String(org.total_employees)} accent="from-brand-600 to-brand-400" icon="◆" />
        <StatTile label="Pending" value={String(org.pending_employees)} accent="from-amber-500 to-orange-500" icon="◷" />
        <StatTile label="Managers" value={String(org.managers)} accent="from-accent-500 to-accent-400" icon="★" />
        <StatTile label="Teams" value={String(org.teams)} accent="from-sky-500 to-cyan-500" icon="◍" />
        <StatTile label="New hires (90d)" value={String(org.new_hires_90d)} accent="from-rose-500 to-pink-500" icon="✦" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Headcount by team</h3>
          <BreakdownBars items={org.headcount_by_team} total={org.active_employees} color="#3f8a63" />
        </div>
        <div className="card p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Employment type</h3>
          <BreakdownBars items={org.employment_type_breakdown} total={org.active_employees} color="#0891b2" />
        </div>
        <div className="card p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Gender</h3>
          <BreakdownBars items={org.gender_breakdown} total={org.active_employees} color="#f9955a" />
        </div>
      </div>
    </div>
  );
}

function BreakdownBars({
  items,
  total,
  color,
}: {
  items: Breakdown[];
  total: number;
  color: string;
}) {
  if (!items || items.length === 0)
    return <p className="text-sm text-slate-400">No data captured yet.</p>;
  const max = Math.max(total, ...items.map((i) => i.count), 1);
  return (
    <div className="space-y-2.5">
      {items.map((it) => (
        <div key={it.label}>
          <div className="mb-0.5 flex items-center justify-between text-xs">
            <span className="text-slate-600">{it.label}</span>
            <span className="font-medium text-slate-500">{it.count}</span>
          </div>
          <div className="h-2 w-full rounded-full bg-slate-100">
            <div
              className="h-2 rounded-full"
              style={{ width: `${Math.round((it.count / max) * 100)}%`, background: color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function MyDashboard() {
  const { me } = useAuth();
  const empId = me?.employee?.id ?? null;
  const { data, loading } = useApi<ReviewHistoryItem[]>(
    empId ? `/api/employees/${empId}/reviews` : null,
  );

  if (loading) return <LoadingSpinner full />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">
          Welcome, {me?.employee?.full_name ?? me?.user.email}
        </h1>
        <p className="text-sm text-slate-500">Your performance review history</p>
      </div>

      {!data || data.length === 0 ? (
        <EmptyState title="No reviews yet" hint="Your completed reviews will appear here." />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="th">Cycle</th>
                <th className="th">Status</th>
                <th className="th">Score</th>
                <th className="th">Summary</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.assignment_id} className="border-t border-slate-100">
                  <td className="td font-medium">
                    {r.cycle_year} · {r.cycle_type.replace("_", " ")}
                  </td>
                  <td className="td">
                    <ReviewStatusBadge status={r.status} />
                  </td>
                  <td className="td">
                    {r.weighted_total !== null ? `${r.weighted_total.toFixed(1)}/100` : "—"}
                  </td>
                  <td className="td text-slate-500">{r.summary_comment ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function Dashboard() {
  const { can } = useAuth();
  return can("view_org") ? <HrDashboard /> : <MyDashboard />;
}
