import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { EmptyState } from "../components/EmptyState";
import { useFeedback } from "../components/feedback";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { PhotoAvatar } from "../components/PhotoAvatar";
import { EmployeeStatusBadge, ErrorText, Modal } from "../components/ui";
import { api } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type { Employee, EmployeeStatus, InviteResult, Role } from "../shared/types";

type StatusFilter = "all" | EmployeeStatus;

export function Employees() {
  const { me, can } = useAuth();
  const { toast, confirm } = useFeedback();
  const isHr = can("manage_people");
  const { data: employees, loading, reload } = useApi<Employee[]>("/api/employees");
  const [showInvite, setShowInvite] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [linkModal, setLinkModal] = useState<{ name: string; link: string } | null>(null);

  const byId = useMemo(
    () => new Map((employees ?? []).map((e) => [e.id, e])),
    [employees],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (employees ?? []).filter((e) => {
      if (isHr && statusFilter !== "all" && e.status !== statusFilter) return false;
      if (!q) return true;
      return (
        e.full_name.toLowerCase().includes(q) ||
        (e.email ?? "").toLowerCase().includes(q) ||
        (e.team ?? "").toLowerCase().includes(q)
      );
    });
  }, [employees, search, statusFilter, isHr]);

  const pendingCount = (employees ?? []).filter((e) => e.status === "pending").length;

  if (loading) return <LoadingSpinner full />;

  const setActive = async (e: Employee, isActive: boolean) => {
    const ok = await confirm({
      title: `${isActive ? "Reactivate" : "Deactivate"} ${e.full_name}?`,
      message: isActive
        ? "They will be able to sign in again."
        : "They will be signed out and blocked from logging in.",
      confirmLabel: isActive ? "Reactivate" : "Deactivate",
      danger: !isActive,
    });
    if (!ok) return;
    setBusyId(e.id);
    try {
      await api.patch(`/api/users/${e.user_id}`, { is_active: isActive });
      toast("success", `${e.full_name} ${isActive ? "reactivated" : "deactivated"}.`);
      reload();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  const copyInvite = async (e: Employee) => {
    setBusyId(e.id);
    try {
      const res = await api.post<InviteResult>(`/api/users/${e.user_id}/resend-invite`);
      if (res.invite_link) {
        try {
          await navigator.clipboard.writeText(res.invite_link);
          toast("success", `Invite link for ${e.full_name} copied to clipboard.`);
        } catch {
          /* clipboard may be blocked; the modal still shows the link to copy */
        }
        setLinkModal({ name: e.full_name, link: res.invite_link });
      }
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not resend invite");
    } finally {
      setBusyId(null);
    }
  };

  const resendAllPending = async () => {
    const pending = (employees ?? []).filter((e) => e.status === "pending");
    const ok = await confirm({
      title: `Resend invites to ${pending.length} pending ${pending.length === 1 ? "person" : "people"}?`,
      message: "Each gets a fresh link; any previous links become invalid.",
      confirmLabel: "Resend all",
    });
    if (!ok) return;
    let done = 0;
    for (const e of pending) {
      try {
        await api.post<InviteResult>(`/api/users/${e.user_id}/resend-invite`);
        done++;
      } catch {
        /* keep going */
      }
    }
    toast("success", `Resent ${done}/${pending.length} invitation(s).`);
    reload();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">Employees</h1>
        <div className="flex items-center gap-2">
          {isHr && pendingCount > 0 && (
            <button className="btn-secondary" onClick={resendAllPending}>
              Resend all pending ({pendingCount})
            </button>
          )}
          {isHr && (
            <button className="btn-primary" onClick={() => setShowInvite(true)}>
              + Invite employee
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          className="input max-w-xs"
          placeholder="Search name, email, or team…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {isHr && (
          <select
            className="input max-w-[10rem]"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="pending">Pending</option>
            <option value="inactive">Inactive</option>
          </select>
        )}
        <span className="text-sm text-slate-400">
          {filtered.length} of {employees?.length ?? 0}
        </span>
      </div>

      {!employees || employees.length === 0 ? (
        <EmptyState title="No employees to show" />
      ) : filtered.length === 0 ? (
        <EmptyState title="No matches" hint="Try a different search or filter." />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead className="bg-slate-50">
              <tr>
                <th className="th">Name</th>
                <th className="th">Title</th>
                <th className="th">Team</th>
                <th className="th">Manager</th>
                {isHr && <th className="th">Status</th>}
                <th className="th text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => {
                const isSelf = e.user_id === me?.user.id;
                return (
                  <tr key={e.id} className="border-t border-slate-100">
                    <td className="td">
                      <div className="flex items-center gap-3">
                        <PhotoAvatar
                          employeeId={e.id}
                          hasPhoto={e.has_photo}
                          className="h-9 w-9 shrink-0 rounded-full bg-slate-100 ring-1 ring-slate-200"
                          iconClassName="h-5 w-5 text-slate-400"
                        />
                        <span className="font-medium text-slate-800">{e.full_name}</span>
                      </div>
                    </td>
                    <td className="td">{e.job_title ?? "—"}</td>
                    <td className="td">{e.team ?? "—"}</td>
                    <td className="td">
                      {e.manager_id ? byId.get(e.manager_id)?.full_name ?? "—" : "—"}
                    </td>
                    {isHr && (
                      <td className="td">
                        <EmployeeStatusBadge status={e.status} />
                      </td>
                    )}
                    <td className="td">
                      <div className="flex items-center justify-end gap-3">
                        <Link
                          to={`/employees/${e.id}`}
                          className="text-brand-600 hover:underline"
                        >
                          View
                        </Link>
                        {isHr && e.status === "pending" && (
                          <button
                            className="text-brand-600 hover:underline disabled:opacity-50"
                            disabled={busyId === e.id}
                            onClick={() => copyInvite(e)}
                          >
                            Copy invite link
                          </button>
                        )}
                        {isHr && !isSelf && e.status === "active" && (
                          <button
                            className="text-red-600 hover:underline disabled:opacity-50"
                            disabled={busyId === e.id}
                            onClick={() => setActive(e, false)}
                          >
                            Deactivate
                          </button>
                        )}
                        {isHr && e.status === "inactive" && (
                          <button
                            className="text-emerald-600 hover:underline disabled:opacity-50"
                            disabled={busyId === e.id}
                            onClick={() => setActive(e, true)}
                          >
                            Reactivate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {linkModal && (
        <Modal title="Invite link" onClose={() => setLinkModal(null)}>
          <p className="text-sm text-slate-600">
            Fresh invite link for <span className="font-medium">{linkModal.name}</span> (copied
            to your clipboard). Any previous link is now invalid.
          </p>
          <div className="mt-3 break-all rounded-md bg-slate-100 p-3 text-xs text-slate-700">
            {linkModal.link}
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button
              className="btn-secondary"
              onClick={() => navigator.clipboard?.writeText(linkModal.link)}
            >
              Copy again
            </button>
            <button className="btn-primary" onClick={() => setLinkModal(null)}>
              Done
            </button>
          </div>
        </Modal>
      )}

      {showInvite && (
        <InviteModal
          managers={employees ?? []}
          onClose={() => setShowInvite(false)}
          onDone={() => {
            setShowInvite(false);
            reload();
          }}
        />
      )}
    </div>
  );
}

function InviteModal({
  managers,
  onClose,
  onDone,
}: {
  managers: Employee[];
  onClose: () => void;
  onDone: () => void;
}) {
  const { can } = useAuth();
  const canManageRoles = can("manage_roles");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("employee");
  const [fullName, setFullName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [team, setTeam] = useState("");
  const [managerId, setManagerId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [link, setLink] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await api.post<InviteResult>("/api/users/invite", {
        email,
        role,
        initial_employee: {
          full_name: fullName,
          job_title: jobTitle || null,
          team: team || null,
          manager_id: managerId ? Number(managerId) : null,
        },
      });
      if (res.invite_link) {
        setLink(res.invite_link);
      } else {
        onDone();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send invite");
    } finally {
      setBusy(false);
    }
  };

  if (link) {
    return (
      <Modal title="Invitation created" onClose={onDone}>
        <p className="text-sm text-slate-600">
          An email was sent (or, in dev, use this link to accept the invite):
        </p>
        <div className="mt-3 break-all rounded-md bg-slate-100 p-3 text-xs text-slate-700">
          {link}
        </div>
        <div className="mt-4 flex justify-end">
          <button className="btn-primary" onClick={onDone}>
            Done
          </button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title="Invite employee" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">Email</label>
          <input
            type="email"
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="label">Full name</label>
          <input
            className="input"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Role</label>
            <select
              className="input"
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
            >
              <option value="employee">Employee</option>
              <option value="manager">Team Lead</option>
              {canManageRoles && (
                <>
                  <option value="hr">HR</option>
                  <option value="executive">Executive</option>
                  <option value="admin">Admin</option>
                </>
              )}
            </select>
          </div>
          <div>
            <label className="label">Team</label>
            <input className="input" value={team} onChange={(e) => setTeam(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="label">Job title</label>
          <input
            className="input"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
          />
        </div>
        <div>
          <label className="label">Manager (reviewer)</label>
          <select
            className="input"
            value={managerId}
            onChange={(e) => setManagerId(e.target.value)}
          >
            <option value="">— none —</option>
            {managers.map((m) => (
              <option key={m.id} value={m.id}>
                {m.full_name}
              </option>
            ))}
          </select>
        </div>
        <ErrorText message={error} />
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Sending…" : "Send invite"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
