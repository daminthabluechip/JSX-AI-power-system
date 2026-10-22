type Props = {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  type?: "text" | "number" | "time" | "date";
  step?: string;
  hint?: string;
  options?: { value: string; label: string }[];
};

export default function Field({ label, name, value, onChange, error, type = "text", step, hint, options }: Props) {
  const style = `mt-1 w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 ${
    error ? "border-red-400" : "border-slate-200"
  }`;
  return (
    <label className="block text-xs font-medium text-slate-600">
      {label}
      {options ? (
        <select name={name} value={value} onChange={(e) => onChange(e.target.value)} className={style}>
          {options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      ) : (
        <input name={name} type={type} step={step} value={value} onChange={(e) => onChange(e.target.value)} className={style} />
      )}
      {hint && !error && <span className="mt-1 block font-normal text-slate-400">{hint}</span>}
      {error && <span className="mt-1 block font-normal text-red-600">{error}</span>}
    </label>
  );
}
