import type { LucideIcon } from "lucide-react";

type Props = {
  label: string;
  value: string | number;
  note?: string;
  icon: LucideIcon;
  tone?: "blue" | "orange" | "green" | "purple";
};

const TONES = {
  blue: "bg-blue-50 text-blue-600",
  orange: "bg-orange-50 text-orange-500",
  green: "bg-emerald-50 text-emerald-600",
  purple: "bg-violet-50 text-violet-600",
};

export default function StatCard({ label, value, note, icon: Icon, tone = "blue" }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between">
        <p className="text-xs text-slate-500">{label}</p>
        <span className={`rounded-lg p-2 ${TONES[tone]}`}>
          <Icon size={16} />
        </span>
      </div>
      <p className="mt-1 text-3xl font-bold">{value}</p>
      {note && <p className="mt-1 text-xs text-emerald-600">{note}</p>}
    </div>
  );
}
