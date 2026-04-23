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
    // Lista contratos atuais (com competência ativa). O endpoint /contratos
    // retorna ContratoCidadeListItem que tem id/uf/cidade/competencia/saldo.
    apiClient
      .get<ContratoItem[]>("/contratos")
      .then((r) => {
        // Dedup por id (um mesmo contrato pode aparecer em múltiplas competências)
        const porId = new Map<string, ContratoItem>()
        for (const c of r.data) {
          if (!porId.has(c.id)) porId.set(c.id, c)
        }
        const unicos = Array.from(porId.values()).sort((a, b) => {
          const ufCmp = (a.uf || "").localeCompare(b.uf || "")
          return ufCmp !== 0 ? ufCmp : (a.cidade || "").localeCompare(b.cidade || "")
        })
        setContratos(unicos)
      })
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
