import { useRef, useState } from "react";
import { EmptyState } from "../components/EmptyState";
import { useFeedback } from "../components/feedback";
import { ErrorText, Modal } from "../components/ui";
import { api, fetchBlob } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type { DocumentKind, EmployeeDocument } from "../shared/types";

const KIND_LABELS: Record<DocumentKind, string> = {
  degree: "Degree / Certificate",
  id_document: "ID Document",
  offer_letter: "Offer Letter",
  employment_letter: "Employment Letter",
  promotion_letter: "Promotion Letter",
  other: "Other",
};

const KIND_ORDER: DocumentKind[] = [
  "offer_letter",
  "employment_letter",
  "promotion_letter",
  "degree",
  "id_document",
  "other",
];

function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function EmployeeDocuments({
  employeeId,
  canManage,
}: {
  employeeId: number;
  canManage: boolean;
}) {
  const { toast, confirm } = useFeedback();
  const { data, loading, error, reload } = useApi<EmployeeDocument[]>(
    `/api/employees/${employeeId}/documents`,
  );
  const [uploading, setUploading] = useState(false);

  // Documents may be forbidden for some viewers — treat 403 as "not visible".
  if (error) return null;

  const docs = data ?? [];
  const grouped = KIND_ORDER.map((k) => ({
    kind: k,
    items: docs.filter((d) => d.kind === k),
  })).filter((g) => g.items.length > 0);

  const download = async (doc: EmployeeDocument) => {
    const blob = await fetchBlob(`/api/employees/${employeeId}/documents/${doc.id}`);
    if (!blob) {
      toast("error", "Could not download file.");
      return;
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = doc.filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const remove = async (doc: EmployeeDocument) => {
    const ok = await confirm({
      title: `Delete "${doc.title}"?`,
      message: "This permanently removes the file.",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.del(`/api/employees/${employeeId}/documents/${doc.id}`);
      toast("success", "Document deleted.");
      reload();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not delete");
    }
  };

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">Documents</h2>
        {canManage && (
          <button className="btn-secondary" onClick={() => setUploading(true)}>
            + Upload document
          </button>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : docs.length === 0 ? (
        <EmptyState
          title="No documents on file"
          hint={canManage ? "Upload offer letters, degrees, IDs, and more." : undefined}
        />
      ) : (
        <div className="space-y-4">
          {grouped.map((g) => (
            <div key={g.kind} className="card overflow-hidden">
              <div className="border-b border-slate-100 bg-slate-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {KIND_LABELS[g.kind]}
              </div>
              <table className="w-full">
                <tbody>
                  {g.items.map((d) => (
                    <tr key={d.id} className="border-t border-slate-100 first:border-t-0">
                      <td className="td">
                        <p className="font-medium text-slate-800">{d.title}</p>
                        <p className="text-xs text-slate-400">
                          {d.filename} · {fileSize(d.size_bytes)} ·{" "}
                          {new Date(d.created_at).toLocaleDateString()}
                        </p>
                      </td>
                      <td className="td text-right whitespace-nowrap">
                        <button
                          className="text-brand-600 hover:underline"
                          onClick={() => download(d)}
                        >
                          Download
                        </button>
                        {canManage && (
                          <button
                            className="ml-3 text-red-600 hover:underline"
                            onClick={() => remove(d)}
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {uploading && (
        <UploadModal
          employeeId={employeeId}
          onClose={() => setUploading(false)}
          onDone={() => {
            setUploading(false);
            reload();
          }}
        />
      )}
    </div>
  );
}

function UploadModal({
  employeeId,
  onClose,
  onDone,
}: {
  employeeId: number;
  onClose: () => void;
  onDone: () => void;
}) {
  const { toast } = useFeedback();
  const [kind, setKind] = useState<DocumentKind>("offer_letter");
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const file = fileInput.current?.files?.[0];
    if (!file) {
      setError("Choose a file to upload.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("kind", kind);
      form.append("title", title.trim() || file.name);
      form.append("file", file);
      await api.form(`/api/employees/${employeeId}/documents`, form);
      toast("success", "Document uploaded.");
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Upload document" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">Type</label>
          <select
            className="input"
            value={kind}
            onChange={(e) => setKind(e.target.value as DocumentKind)}
          >
            {KIND_ORDER.map((k) => (
              <option key={k} value={k}>
                {KIND_LABELS[k]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Title</label>
          <input
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Offer Letter 2024"
          />
        </div>
        <div>
          <label className="label">File</label>
          <input
            ref={fileInput}
            type="file"
            className="input"
            accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.doc,.docx,.xls,.xlsx,.txt"
          />
          <p className="mt-1 text-xs text-slate-400">PDF, images, or Office docs · up to 15 MB</p>
        </div>
        <ErrorText message={error} />
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Uploading…" : "Upload"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
