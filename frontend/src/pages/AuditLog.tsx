import { EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { useApi } from "../lib/useApi";
import type { AuditEntry } from "../shared/types";

const ACTION_LABELS: Record<string, string> = {
  "user.invite": "Invited user",
  "user.resend_invite": "Resent invite",
  "user.update": "Updated user",
  "user.deactivate": "Deactivated user",
  "cycle.create": "Created cycle",
  "cycle.assign": "Assigned reviewers",
  "cycle.open": "Opened cycle",
  "cycle.close": "Closed cycle",
  "kpi.create": "Created KPI",
  "kpi.deactivate": "Deactivated KPI",
};

export function AuditLog() {
  const { data, loading } = useApi<AuditEntry[]>("/api/audit?limit=200");

  if (loading) return <LoadingSpinner full />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Audit Log</h1>
        <p className="text-sm text-slate-500">Every privileged action, most recent first</p>
      </div>

      {!data || data.length === 0 ? (
        <EmptyState title="No activity yet" />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[720px]">
            <thead className="bg-slate-50">
              <tr>
                <th className="th">When</th>
                <th className="th">Actor</th>
                <th className="th">Action</th>
                <th className="th">Target</th>
                <th className="th">Detail</th>
              </tr>
            </thead>
            <tbody>
              {data.map((e) => (
                <tr key={e.id} className="border-t border-slate-100">
                  <td className="td whitespace-nowrap text-slate-500">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="td">{e.actor_email ?? "—"}</td>
                  <td className="td font-medium">{ACTION_LABELS[e.action] ?? e.action}</td>
                  <td className="td text-slate-500">
                    {e.target_type ? `${e.target_type} #${e.target_id}` : "—"}
                  </td>
                  <td className="td text-xs text-slate-500">
                    {e.detail ? JSON.stringify(e.detail) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
