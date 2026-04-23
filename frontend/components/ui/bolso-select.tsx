"use client"
import type { BolsoTipo } from "@/types/v2"
import { BOLSO_LABELS } from "@/types/v2"

interface Props {
  value: BolsoTipo
  onChange: (v: BolsoTipo) => void
  disabled?: boolean
}

export function BolsoSelect({ value, onChange, disabled }: Props) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as BolsoTipo)}
      disabled={disabled}
      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white"
    >
      {(Object.keys(BOLSO_LABELS) as BolsoTipo[]).map((b) => (
        <option key={b} value={b}>
          {BOLSO_LABELS[b]}
        </option>
      ))}
    </select>
  )
}
