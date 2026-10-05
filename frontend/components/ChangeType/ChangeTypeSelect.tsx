import type { ChangeType } from "@/types";

export const CHANGE_TYPES: { id: ChangeType; label: string; product: string }[] = [
  { id: "ground", label: "Ground movement", product: "GUNW" },
  { id: "wetland", label: "Wetland and water", product: "GCOV, GSLC" },
  { id: "farming", label: "Farming", product: "GCOV, SME2" },
  { id: "forest", label: "Forest disturbance", product: "GCOV, GSLC" },
  { id: "glacier", label: "Glacier movement", product: "GOFF" },
  { id: "infrastructure", label: "Infrastructure", product: "GUNW, GCOV" },
  { id: "auto", label: "Auto detect", product: "all products" },
];

export default function ChangeTypeSelect({ value, onChange }: { value: ChangeType; onChange: (c: ChangeType) => void }) {
  return (
    <div role="radiogroup" aria-label="Change type" className="types">
      {CHANGE_TYPES.map((t) => (
        <button key={t.id} role="radio" aria-checked={value === t.id}
          className={value === t.id ? "type on" : "type"} onClick={() => onChange(t.id)}>
          <span>{t.label}</span><small>{t.product}</small>
        </button>
      ))}
    </div>
  );
}
