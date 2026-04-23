"use client"

import { useEffect, useState } from "react"
import { apiClient } from "@/lib/api"

interface ContratoItem {
  id: string
  uf: string
  cidade: string
  competencia?: string
}

interface Props {
  value: string | null
  onChange: (id: string | null) => void
  disabled?: boolean
}

export function ContratoSelect({ value, onChange, disabled }: Props) {
  const [contratos, setContratos] = useState<ContratoItem[]>([])

  useEffect(() => {
    // Lista todos os contratos cadastrados (sem filtro por competência).
    // /contratos (antigo) filtra por mes_competencia, ficando vazio em meses
    // sem rodada PP — por isso usamos /contratos/cadastrados.
    apiClient
      .get<ContratoItem[]>("/contratos/cadastrados")
      .then((r) => setContratos(r.data))
      .catch(() => setContratos([]))
  }, [])

  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      disabled={disabled}
      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white"
    >
      <option value="">— Sem contrato vinculado —</option>
      {contratos.map((c) => (
        <option key={c.id} value={c.id}>
          {c.uf} — {c.cidade}
        </option>
      ))}
    </select>
  )
}
