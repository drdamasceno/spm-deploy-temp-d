"use client"

import { formatBRL } from "@/lib/format"
import type { RecebiveisResponse } from "@/types/v2"

interface RecebiveisCardProps {
  data: RecebiveisResponse
}

function maiorFaixaAging(porAging: Record<string, number> | undefined): string | null {
  if (!porAging) return null
  let maiorFaixa: string | null = null
  let maiorValor = -Infinity
  for (const [faixa, valor] of Object.entries(porAging)) {
    if (typeof valor === "number" && valor > maiorValor) {
      maiorValor = valor
      maiorFaixa = faixa
    }
  }
  return maiorFaixa
}

export function RecebiveisCard({ data }: RecebiveisCardProps) {
  const contratantesDistintos = new Set(
    (data.itens ?? []).map((i) => i.contratante).filter(Boolean)
  ).size
  const faixaMaior = maiorFaixaAging(data.por_aging)
  return (
    <a
      href="/dashboard/recebiveis"
      className="block rounded-xl border border-red-300 bg-red-50 p-5 shadow-sm transition hover:shadow-md hover:border-red-400"
    >
      <div className="text-xs font-bold uppercase tracking-wide text-red-800">
        ⚠ Recebíveis em atraso
      </div>
      <div className="mt-2 text-2xl font-bold tabular-nums text-slate-900">
        {formatBRL(data.total)}
      </div>
      <div className="mt-1 text-xs text-slate-500">
        {contratantesDistintos} contratante{contratantesDistintos === 1 ? "" : "s"}
        {faixaMaior ? ` · maior faixa ${faixaMaior}` : ""} →
      </div>
    </a>
  )
}
