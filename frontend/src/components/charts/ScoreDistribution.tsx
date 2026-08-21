import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { StatusBucket } from "../../shared/types";

export function ScoreDistribution({ data }: { data: StatusBucket[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: -16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#64748b" }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#64748b" }} />
        <Tooltip
          cursor={{ fill: "#f1f5f9" }}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}
        />
        <Bar dataKey="count" fill="#297c67" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
