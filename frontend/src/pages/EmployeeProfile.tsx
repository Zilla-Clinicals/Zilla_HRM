import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { useFeedback } from "../components/feedback";
import { GoalsPanel } from "../components/GoalsPanel";
import { PhotoAvatar } from "../components/PhotoAvatar";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { EmployeeStatusBadge, ErrorText, Modal, ReviewStatusBadge } from "../components/ui";
import { api } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import { EmployeeDocuments } from "./EmployeeDocuments";
import type { Employee, ReviewHistoryItem } from "../shared/types";

const GENDER = { male: "Male", female: "Female", other: "Other", prefer_not_to_say: "Undisclosed" };
const MARITAL = { single: "Single", married: "Married", divorced: "Divorced", widowed: "Widowed" };
const EMPLOYMENT = {
  full_time: "Full-time",
  part_time: "Part-time",
  contract: "Contract",
  intern: "Intern",
};

function age(dob: string | null): string | null {
  if (!dob) return null;
  const d = new Date(dob);
  const now = new Date();
  let a = now.getFullYear() - d.getFullYear();
  const m = now.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < d.getDate())) a--;
  return a >= 0 && a < 120 ? `${a} yrs` : null;
}

export function EmployeeProfile() {
  const { id } = useParams();
  const { can, me } = useAuth();
  const isHr = can("manage_people");
  const { data: emp, loading, reload } = useApi<Employee>(id ? `/api/employees/${id}` : null);
  const { data: allEmployees } = useApi<Employee[]>(isHr ? "/api/employees" : null);
  const { data: history } = useApi<ReviewHistoryItem[]>(
    id ? `/api/employees/${id}/reviews` : null,
  );
  const { toast, confirm } = useFeedback();
  const [editing, setEditing] = useState(false);
  const [tab, setTab] = useState<"about" | "goals" | "documents" | "reviews">("about");
  const [photoKey, setPhotoKey] = useState(0);
  const [photoBusy, setPhotoBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const uploadPhoto = async (file: File) => {
    setPhotoBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      await api.form(`/api/employees/${id}/photo`, form);
      toast("success", "Photo updated.");
      setPhotoKey((k) => k + 1);
      reload();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not upload photo");
    } finally {
      setPhotoBusy(false);
    }
  };

  const removePhoto = async () => {
    if (!(await confirm({ title: "Remove photo?", confirmLabel: "Remove", danger: true }))) return;
    setPhotoBusy(true);
    try {
      await api.del(`/api/employees/${id}/photo`);
      toast("success", "Photo removed.");
      setPhotoKey((k) => k + 1);
      reload();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not remove photo");
    } finally {
      setPhotoBusy(false);
    }
  };

  if (loading) return <LoadingSpinner full />;
  if (!emp) return <p className="text-sm text-slate-500">Employee not found.</p>;

  const managerName =
    emp.manager_id && allEmployees
      ? allEmployees.find((e) => e.id === emp.manager_id)?.full_name ?? "—"
      : emp.manager_id
        ? `#${emp.manager_id}`
        : "—";

  const dob = emp.date_of_birth ? `${emp.date_of_birth}${age(emp.date_of_birth) ? ` · ${age(emp.date_of_birth)}` : ""}` : null;
  const subtitle = [emp.job_title, emp.team].filter(Boolean).join(" · ") || "No role or team set";

  return (
    <div className="space-y-6">
      <Link to="/employees" className="text-sm text-brand-600 hover:underline">
        ← Back to employees
      </Link>

      {/* Header */}
      <div className="card overflow-hidden p-0">
        <div className="h-24 bg-brand-gradient" />
        <div className="px-6 pb-6">
          {/* Avatar overlaps the cover band */}
          <div className="relative -mt-12 h-24 w-24">
            <PhotoAvatar
              employeeId={emp.id}
              hasPhoto={emp.has_photo}
              refreshKey={photoKey}
              className="h-24 w-24 rounded-2xl bg-white shadow-card ring-4 ring-white"
              iconClassName="h-12 w-12 text-brand-300"
            />
            {isHr && (
              <>
                <input
                  ref={fileInput}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) uploadPhoto(f);
                    e.target.value = "";
                  }}
                />
                <button
                  type="button"
                  disabled={photoBusy}
                  onClick={() => fileInput.current?.click()}
                  title="Upload / change photo"
                  className="absolute -bottom-1.5 -right-1.5 grid h-8 w-8 place-items-center rounded-full bg-brand-600 text-sm text-white shadow-glow-sm ring-2 ring-white transition hover:bg-brand-700 disabled:opacity-50"
                >
                  {photoBusy ? "…" : "📷"}
                </button>
              </>
            )}
          </div>

          <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-2xl font-bold tracking-tight text-slate-800">
                  {emp.full_name}
                </h1>
                {emp.employee_number && (
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-xs font-medium text-slate-500">
                    {emp.employee_number}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
            </div>
            <div className="flex items-center gap-3">
              {isHr && <EmployeeStatusBadge status={emp.status} />}
              {isHr && emp.has_photo && (
                <button
                  className="btn-secondary"
                  disabled={photoBusy}
                  onClick={removePhoto}
                >
                  Remove photo
                </button>
              )}
              {isHr && (
                <button className="btn-primary" onClick={() => setEditing(true)}>
                  Edit details
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs — the bio sits under its own "About" tab (HR/management view) */}
      <div className="flex gap-1 overflow-x-auto border-b border-slate-200">
        {(
          [
            ["about", "About"],
            ["goals", "Goals"],
            ["documents", "Documents"],
            ["reviews", "Reviews"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`relative shrink-0 px-4 py-2.5 text-sm font-medium transition-colors ${
              tab === key ? "text-brand-700" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {label}
            {tab === key && (
              <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-brand-600" />
            )}
          </button>
        ))}
      </div>

      {tab === "about" && (
      <div className="grid gap-6 lg:grid-cols-3">
        <Section title="Personal">
          <Field label="Date of birth" value={dob} />
          <Field label="Gender" value={emp.gender ? GENDER[emp.gender] : null} />
          <Field label="Marital status" value={emp.marital_status ? MARITAL[emp.marital_status] : null} />
          <Field label="Nationality" value={emp.nationality} />
          <Field label="Personal email" value={emp.personal_email} />
          <Field label="Phone" value={emp.phone} />
          <Field
            label="Address"
            value={[emp.address, emp.city, emp.country].filter(Boolean).join(", ") || null}
          />
        </Section>

        <Section title="Employment">
          <Field label="Employee no." value={emp.employee_number} />
          <Field label="Work email" value={emp.email} />
          <Field label="Job title" value={emp.job_title} />
          <Field label="Team / Dept" value={emp.team} />
          <Field label="Employment type" value={emp.employment_type ? EMPLOYMENT[emp.employment_type] : null} />
          <Field label="Work location" value={emp.work_location} />
          <Field label="Hire date" value={emp.hire_date} />
          <Field label="Manager" value={managerName} />
        </Section>

        <Section title="Emergency contact">
          <Field label="Name" value={emp.emergency_contact_name} />
          <Field label="Phone" value={emp.emergency_contact_phone} />
          <Field label="Relationship" value={emp.emergency_contact_relationship} />
        </Section>
      </div>
      )}

      {tab === "goals" && (
        <GoalsPanel
          employeeId={emp.id}
          canEdit={me?.employee?.id === emp.id}
          heading="Goals"
        />
      )}

      {tab === "documents" && <EmployeeDocuments employeeId={emp.id} canManage={isHr} />}

      {tab === "reviews" && (
      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Review history</h2>
        {!history || history.length === 0 ? (
          <p className="text-sm text-slate-500">No reviews recorded.</p>
        ) : (
          <div className="space-y-4">
            {history.map((h) => (
              <div key={h.assignment_id} className="card p-4">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-slate-800">
                    {h.cycle_year} · {h.cycle_type.replace("_", " ")}
                  </p>
                  <div className="flex items-center gap-3">
                    <ReviewStatusBadge status={h.status} />
                    <span className="text-sm font-semibold text-slate-700">
                      {h.weighted_total !== null ? `${h.weighted_total.toFixed(1)}/100` : "—"}
                    </span>
                  </div>
                </div>
                {h.summary_comment && (
                  <p className="mt-2 text-sm text-slate-600">{h.summary_comment}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      )}

      {editing && emp && (
        <EditModal
          emp={emp}
          managers={(allEmployees ?? []).filter((e) => e.id !== emp.id)}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            reload();
          }}
        />
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <h2 className="mb-3 text-sm font-semibold text-slate-700">{title}</h2>
      <dl className="space-y-2.5">{children}</dl>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex items-start justify-between gap-4 text-sm">
      <dt className="shrink-0 text-slate-400">{label}</dt>
      <dd className="text-right font-medium text-slate-700">{value || "—"}</dd>
    </div>
  );
}

type FormState = Record<string, string>;

function EditModal({
  emp,
  managers,
  onClose,
  onSaved,
}: {
  emp: Employee;
  managers: Employee[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const { toast } = useFeedback();
  const init: FormState = {
    full_name: emp.full_name ?? "",
    date_of_birth: emp.date_of_birth ?? "",
    gender: emp.gender ?? "",
    marital_status: emp.marital_status ?? "",
    nationality: emp.nationality ?? "",
    personal_email: emp.personal_email ?? "",
    phone: emp.phone ?? "",
    address: emp.address ?? "",
    city: emp.city ?? "",
    country: emp.country ?? "",
    employee_number: emp.employee_number ?? "",
    job_title: emp.job_title ?? "",
    team: emp.team ?? "",
    employment_type: emp.employment_type ?? "",
    work_location: emp.work_location ?? "",
    hire_date: emp.hire_date ?? "",
    manager_id: emp.manager_id ? String(emp.manager_id) : "",
    emergency_contact_name: emp.emergency_contact_name ?? "",
    emergency_contact_phone: emp.emergency_contact_phone ?? "",
    emergency_contact_relationship: emp.emergency_contact_relationship ?? "",
  };
  const [f, setF] = useState<FormState>(init);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: string) => setF((prev) => ({ ...prev, [k]: v }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    // Empty strings -> null; manager_id -> number
    const body: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(f)) {
      if (k === "manager_id") body[k] = v ? Number(v) : null;
      else body[k] = v.trim() === "" ? null : v.trim();
    }
    try {
      await api.patch(`/api/employees/${emp.id}`, body);
      toast("success", "Employee details updated.");
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={`Edit · ${emp.full_name}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-5">
        <fieldset className="space-y-3">
          <legend className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Personal
          </legend>
          <Text label="Full name" value={f.full_name} onChange={(v) => set("full_name", v)} required />
          <div className="grid grid-cols-2 gap-3">
            <Text label="Date of birth" type="date" value={f.date_of_birth} onChange={(v) => set("date_of_birth", v)} />
            <Select
              label="Gender"
              value={f.gender}
              onChange={(v) => set("gender", v)}
              options={[["male", "Male"], ["female", "Female"], ["other", "Other"], ["prefer_not_to_say", "Undisclosed"]]}
            />
            <Select
              label="Marital status"
              value={f.marital_status}
              onChange={(v) => set("marital_status", v)}
              options={[["single", "Single"], ["married", "Married"], ["divorced", "Divorced"], ["widowed", "Widowed"]]}
            />
            <Text label="Nationality" value={f.nationality} onChange={(v) => set("nationality", v)} />
            <Text label="Personal email" type="email" value={f.personal_email} onChange={(v) => set("personal_email", v)} />
            <Text label="Phone" value={f.phone} onChange={(v) => set("phone", v)} />
          </div>
          <Text label="Address" value={f.address} onChange={(v) => set("address", v)} />
          <div className="grid grid-cols-2 gap-3">
            <Text label="City" value={f.city} onChange={(v) => set("city", v)} />
            <Text label="Country" value={f.country} onChange={(v) => set("country", v)} />
          </div>
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Employment
          </legend>
          <div className="grid grid-cols-2 gap-3">
            <Text
              label="Employee no."
              value={f.employee_number}
              onChange={(v) => set("employee_number", v)}
              hint="Auto-generated · must be unique"
            />
            <Text label="Job title" value={f.job_title} onChange={(v) => set("job_title", v)} />
            <Text label="Team / Dept" value={f.team} onChange={(v) => set("team", v)} />
            <Select
              label="Employment type"
              value={f.employment_type}
              onChange={(v) => set("employment_type", v)}
              options={[["full_time", "Full-time"], ["part_time", "Part-time"], ["contract", "Contract"], ["intern", "Intern"]]}
            />
            <Text label="Work location" value={f.work_location} onChange={(v) => set("work_location", v)} />
            <Text label="Hire date" type="date" value={f.hire_date} onChange={(v) => set("hire_date", v)} />
          </div>
          <div>
            <label className="label">Manager</label>
            <select className="input" value={f.manager_id} onChange={(e) => set("manager_id", e.target.value)}>
              <option value="">— none —</option>
              {managers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name}
                </option>
              ))}
            </select>
          </div>
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Emergency contact
          </legend>
          <div className="grid grid-cols-2 gap-3">
            <Text label="Name" value={f.emergency_contact_name} onChange={(v) => set("emergency_contact_name", v)} />
            <Text label="Phone" value={f.emergency_contact_phone} onChange={(v) => set("emergency_contact_phone", v)} />
          </div>
          <Text
            label="Relationship"
            value={f.emergency_contact_relationship}
            onChange={(v) => set("emergency_contact_relationship", v)}
          />
        </fieldset>

        <ErrorText message={error} />
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Text({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  hint?: string;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <input
        className="input"
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
      />
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">—</option>
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </div>
  );
}
