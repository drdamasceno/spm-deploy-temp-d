"use client"
import { useEffect, useState } from "react"
import { apiClient } from "@/lib/api"
import type { EmpresaGrupo } from "@/types/v2"

interface Props {
  value: string | null
  onChange: (id: string | null) => void
  disabled?: boolean
}

export function EmpresaPagadoraSelect({ value, onChange, disabled }: Props) {
  const [empresas, setEmpresas] = useState<EmpresaGrupo[]>([])

  useEffect(() => {
    apiClient
      .get<EmpresaGrupo[]>("/empresas")
      .then((r) => setEmpresas(r.data))
      .catch(() => setEmpresas([]))
  }, [])

  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      disabled={disabled}
      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white"
    >
      <option value="">— Nenhuma (pago direto pela empresa do orçamento) —</option>
      {empresas.map((e) => (
        <option key={e.id} value={e.id}>
          {e.codigo} — {e.razao_social}
        </option>
      ))}
    </select>
  )
}
