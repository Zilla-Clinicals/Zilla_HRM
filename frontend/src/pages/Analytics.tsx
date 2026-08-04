import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { api } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type {
  AnalyticsEmployees,
  AnalyticsSummary,
  CycleAnalytics,
} from "../shared/types";

const PALETTE = ["#2563eb", "#16a34a", "#d97706", "#db2777", "#7c3aed", "#0891b2", "#dc2626"];
const axis = { fontSize: 12, fill: "#64748b" };
const tooltipStyle = { fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" };

function Card({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
      {hint && <p className="mb-2 text-xs text-slate-400">{hint}</p>}
      <div className={hint ? "" : "mt-3"}>{children}</div>
    </div>
  );
}

export function Analytics() {
  const { data: summary, loading } = useApi<AnalyticsSummary>("/api/analytics/summary");
  const { data: employees } = useApi<AnalyticsEmployees>("/api/analytics/employees");
  const [cycleId, setCycleId] = useState<number | null>(null);
  const [cycleData, setCycleData] = useState<CycleAnalytics | null>(null);

  useEffect(() => {
    if (summary?.latest_cycle_id && cycleId === null) setCycleId(summary.latest_cycle_id);
  }, [summary, cycleId]);

  useEffect(() => {
    if (cycleId === null) return;
    api.get<CycleAnalytics>(`/api/analytics/cycle/${cycleId}`).then(setCycleData);
  }, [cycleId]);

  const labels = summary?.cycles.map((c) => c.label) ?? [];

  const trendRows = useMemo(
    () =>
      (summary?.cycles ?? []).map((c) => ({
        label: c.label,
        Score: c.avg_score,
        "Completion %": Math.round(c.completion_rate * 100),
      })),
    [summary],
  );

  // Category trend as % of each category's max, so categories are comparable.
  const categoryRows = useMemo(() => {
    if (!summary) return [];
    return labels.map((label, i) => {
      const row: Record<string, number | string | null> = { label };
      for (const s of summary.category_series) {
        const v = s.values[i];
        row[s.name] = v !== null && s.max_points ? Math.round((v / s.max_points) * 100) : null;
      }
      return row;
    });
  }, [summary, labels]);

  const teamRows = useMemo(() => {
    if (!summary) return [];
    return labels.map((label, i) => {
      const row: Record<string, number | string | null> = { label };
      for (const s of summary.team_series) row[s.name] = s.values[i];
      return row;
    });
  }, [summary, labels]);

  if (loading) return <LoadingSpinner full />;
  if (!summary || summary.cycles.length === 0) {
    return (
      <EmptyState
        title="No analytics yet"
        hint="Open a review cycle and record some scores to see trends here."
      />
    );
  }

  const calibrationRows = (cycleData?.calibration ?? []).map((c) => ({
    category: c.category,
    Self: Math.round(c.self_pct * 100),
    Manager: Math.round(c.reviewer_pct * 100),
  }));

  const kpisSorted = [...(cycleData?.kpis ?? [])].sort((a, b) => a.pct - b.pct);
  const weakest = kpisSorted.slice(0, 6);
  const strongest = [...kpisSorted].reverse().slice(0, 6);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Analytics</h1>
          <p className="text-sm text-slate-500">Performance across review cycles</p>
        </div>
        {cycleId !== null && (
          <label className="flex items-center gap-2 text-sm text-slate-500">
            Cycle detail
            <select
              className="input max-w-xs"
              value={cycleId}
              onChange={(e) => setCycleId(Number(e.target.value))}
            >
              {summary.cycles.map((c) => (
                <option key={c.cycle_id} value={c.cycle_id}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {/* Trend: score + completion over cycles */}
      <Card title="Company score & completion trend" hint="Average official score (/100) and completion % per cycle">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={trendRows} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="label" tick={axis} />
            <YAxis domain={[0, 100]} tick={axis} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line type="monotone" dataKey="Score" stroke="#2563eb" strokeWidth={2} connectNulls />
            <Line
              type="monotone"
              dataKey="Completion %"
              stroke="#16a34a"
              strokeWidth={2}
              strokeDasharray="4 3"
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Category trends */}
        <Card title="Category performance trend" hint="% of each category's max points, per cycle">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={categoryRows} margin={{ top: 8, right: 8, bottom: 4, left: -12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="label" tick={axis} />
              <YAxis domain={[0, 100]} tick={axis} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {summary.category_series.map((s, i) => (
                <Line
                  key={s.name}
                  type="monotone"
                  dataKey={s.name}
                  stroke={PALETTE[i % PALETTE.length]}
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Team trends */}
        <Card title="Team performance trend" hint="Average score (/100) by team, per cycle">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={teamRows} margin={{ top: 8, right: 8, bottom: 4, left: -12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="label" tick={axis} />
              <YAxis domain={[0, 100]} tick={axis} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {summary.team_series.map((s, i) => (
                <Line
                  key={s.name}
                  type="monotone"
                  dataKey={s.name}
                  stroke={PALETTE[i % PALETTE.length]}
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Self vs Manager calibration for the selected cycle */}
      <Card
        title={`Self vs. Manager calibration — ${cycleData?.label ?? ""}`}
        hint={
          cycleData && cycleData.calibration_pairs > 0
            ? `Where employees rate themselves vs. their manager, by category (${cycleData.calibration_pairs} employee(s) with both submitted)`
            : "No employees have both a submitted self-assessment and a manager review in this cycle yet."
        }
      >
        {cycleData && cycleData.calibration_pairs > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={calibrationRows} margin={{ top: 8, right: 8, bottom: 40, left: -12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="category" tick={axis} angle={-20} textAnchor="end" height={60} interval={0} />
              <YAxis domain={[0, 100]} tick={axis} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Self" fill="#94a3b8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Manager" fill="#2563eb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-slate-400">Nothing to compare yet.</p>
        )}
      </Card>

      {/* KPI strengths / weaknesses */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Weakest KPIs" hint={`Lowest average score in ${cycleData?.label ?? "the cycle"}`}>
          <KpiBars items={weakest} color="#dc2626" />
        </Card>
        <Card title="Strongest KPIs" hint={`Highest average score in ${cycleData?.label ?? "the cycle"}`}>
          <KpiBars items={strongest} color="#16a34a" />
        </Card>
      </div>

      {/* Employee trajectories */}
      <Card title="Employee performance across cycles" hint="Official score (/100) each cycle; ▲/▼ is the change from the prior cycle">
        {!employees || employees.employees.length === 0 ? (
          <p className="text-sm text-slate-400">No employee scores yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px]">
              <thead className="bg-slate-50">
                <tr>
                  <th className="th">Employee</th>
                  <th className="th">Team</th>
                  {employees.cycles.map((c) => (
                    <th key={c} className="th text-right">
                      {c}
                    </th>
                  ))}
                  <th className="th text-right">Trend</th>
                </tr>
              </thead>
              <tbody>
                {employees.employees.map((e) => (
                  <tr key={e.employee_id} className="border-t border-slate-100">
                    <td className="td font-medium">{e.name}</td>
                    <td className="td text-slate-500">{e.team ?? "—"}</td>
                    {e.values.map((v, i) => (
                      <td key={i} className="td text-right">
                        {v !== null ? v.toFixed(1) : "—"}
                      </td>
                    ))}
                    <td className="td text-right">
                      {e.delta === null ? (
                        <span className="text-slate-400">—</span>
                      ) : e.delta >= 0 ? (
                        <span className="text-emerald-600">▲ {e.delta.toFixed(1)}</span>
                      ) : (
                        <span className="text-red-600">▼ {Math.abs(e.delta).toFixed(1)}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function KpiBars({
  items,
  color,
}: {
  items: { name: string; pct: number; earned_avg: number; max_points: number }[];
  color: string;
}) {
  if (items.length === 0) return <p className="text-sm text-slate-400">No data.</p>;
  return (
    <div className="space-y-2">
      {items.map((k) => (
        <div key={k.name}>
          <div className="mb-0.5 flex items-center justify-between text-xs">
            <span className="truncate pr-2 text-slate-700">{k.name}</span>
            <span className="whitespace-nowrap text-slate-500">
              {k.earned_avg.toFixed(2)}/{k.max_points} · {Math.round(k.pct * 100)}%
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-slate-100">
            <div
              className="h-2 rounded-full"
              style={{ width: `${Math.round(k.pct * 100)}%`, background: color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
