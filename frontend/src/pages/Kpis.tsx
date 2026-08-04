import { useState } from "react";
import { EmptyState } from "../components/EmptyState";
import { useFeedback } from "../components/feedback";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorText, Modal } from "../components/ui";
import { api } from "../lib/apiClient";
import { useApi } from "../lib/useApi";
import type { Kpi, KpiCategory } from "../shared/types";

export function Kpis() {
  const { toast, confirm } = useFeedback();
  const { data: kpis, loading, reload } = useApi<Kpi[]>("/api/kpis");
  const { data: categories, reload: reloadCats } = useApi<KpiCategory[]>(
    "/api/kpis/categories",
  );
  const [editing, setEditing] = useState<Kpi | "new" | null>(null);

  if (loading) return <LoadingSpinner full />;

  const cats = categories ?? [];
  const totalWeight = cats.reduce((s, c) => s + Number(c.weight), 0);
  const byCategory = new Map<string, Kpi[]>();
  for (const k of kpis ?? []) {
    if (!byCategory.has(k.category)) byCategory.set(k.category, []);
    byCategory.get(k.category)!.push(k);
  }

  const remove = async (k: Kpi) => {
    const ok = await confirm({
      title: `Deactivate "${k.name}"?`,
      message: "It stays on past reviews but won't appear on new ones.",
      confirmLabel: "Deactivate",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.del(`/api/kpis/${k.id}`);
      toast("success", `${k.name} deactivated.`);
      reload();
      reloadCats();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not deactivate");
    }
  };

  const saveWeight = async (cat: KpiCategory, weight: number) => {
    if (weight === Number(cat.weight)) return;
    try {
      await api.patch(`/api/kpis/categories/${cat.id}`, { weight });
      toast("success", `${cat.name} weight updated.`);
      reloadCats();
      reload();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not update weight");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">KPI Catalog</h1>
          <p className="text-sm text-slate-500">
            Five weighted categories · points total{" "}
            <span className={totalWeight === 100 ? "text-emerald-600" : "text-amber-600"}>
              {totalWeight}/100
            </span>
          </p>
        </div>
        <button className="btn-primary" onClick={() => setEditing("new")}>
          + New KPI
        </button>
      </div>

      {cats.length === 0 ? (
        <EmptyState title="No categories configured" />
      ) : (
        <div className="space-y-6">
          {cats.map((cat) => {
            const items = byCategory.get(cat.name) ?? [];
            return (
              <div key={cat.id} className="card overflow-hidden">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-700">{cat.name}</p>
                    <p className="text-xs text-slate-500">
                      {cat.kpi_count} KPIs · {cat.points_per_kpi} pts each
                    </p>
                  </div>
                  <label className="flex items-center gap-2 text-xs text-slate-500">
                    weight
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={1}
                      defaultValue={Number(cat.weight)}
                      className="input w-20 py-1"
                      onBlur={(e) => saveWeight(cat, Number(e.target.value))}
                    />
                  </label>
                </div>
                <table className="w-full">
                  <tbody>
                    {items.map((k) => (
                      <tr key={k.id} className="border-t border-slate-100 first:border-t-0">
                        <td className="td align-top">
                          <p className="font-medium text-slate-800">{k.name}</p>
                          {k.description && (
                            <p className="text-xs text-slate-500">{k.description}</p>
                          )}
                        </td>
                        <td className="td align-top text-xs text-slate-500">
                          {k.measurement && (
                            <p>
                              <span className="text-slate-400">Measure:</span> {k.measurement}
                            </p>
                          )}
                          {k.target && (
                            <p>
                              <span className="text-slate-400">Target:</span> {k.target}
                            </p>
                          )}
                        </td>
                        <td className="td align-top whitespace-nowrap text-slate-600">
                          {k.points} pts
                        </td>
                        <td className="td align-top text-right whitespace-nowrap">
                          <button
                            className="text-brand-600 hover:underline"
                            onClick={() => setEditing(k)}
                          >
                            Edit
                          </button>
                          <button
                            className="ml-3 text-red-600 hover:underline"
                            onClick={() => remove(k)}
                          >
                            Deactivate
                          </button>
                        </td>
                      </tr>
                    ))}
                    {items.length === 0 && (
                      <tr>
                        <td className="td text-sm text-slate-400" colSpan={4}>
                          No KPIs in this category.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      )}

      {editing && (
        <KpiModal
          kpi={editing === "new" ? null : editing}
          categories={cats}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
            reloadCats();
          }}
        />
      )}
    </div>
  );
}

function KpiModal({
  kpi,
  categories,
  onClose,
  onSaved,
}: {
  kpi: Kpi | null;
  categories: KpiCategory[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(kpi?.name ?? "");
  const [category, setCategory] = useState(kpi?.category ?? categories[0]?.name ?? "");
  const [description, setDescription] = useState(kpi?.description ?? "");
  const [measurement, setMeasurement] = useState(kpi?.measurement ?? "");
  const [target, setTarget] = useState(kpi?.target ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = {
        name,
        category,
        description: description || null,
        measurement: measurement || null,
        target: target || null,
      };
      if (kpi) {
        await api.patch(`/api/kpis/${kpi.id}`, body);
      } else {
        await api.post("/api/kpis", body);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save KPI");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={kpi ? "Edit KPI" : "New KPI"} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">Name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div>
          <label className="label">Category</label>
          <select
            className="input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            required
          >
            {categories.map((c) => (
              <option key={c.id} value={c.name}>
                {c.name} ({Number(c.weight)} pts)
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Description</label>
          <textarea
            className="input"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Measurement</label>
            <input
              className="input"
              value={measurement}
              onChange={(e) => setMeasurement(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Target</label>
            <input className="input" value={target} onChange={(e) => setTarget(e.target.value)} />
          </div>
        </div>
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
