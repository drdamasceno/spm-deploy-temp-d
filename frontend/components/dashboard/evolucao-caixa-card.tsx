"use client"

import { Sparkline } from "@/components/ui/sparkline"
import { formatBRL } from "@/lib/format"
import type { EvolucaoCaixaResponse } from "@/types/v2"

interface EvolucaoCaixaCardProps {
  data: EvolucaoCaixaResponse
}

function fmtDiaMes(iso: string): string {
  if (!iso) return "—"
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (m) {
    const [, , mm, dd] = m
    return `${dd}/${mm}`
  }
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const dd = String(d.getDate()).padStart(2, "0")
  const mm = String(d.getMonth() + 1).padStart(2, "0")
  return `${dd}/${mm}`
}

export function EvolucaoCaixaCard({ data }: EvolucaoCaixaCardProps) {
  const positivo = data.variacao_valor >= 0
  const corVariacao = positivo ? "text-emerald-700" : "text-red-700"
  const sinal = positivo ? "+" : ""
  return (
    <a
      href="/dashboard/saldo-diario"
      className="block rounded-xl border-2 border-blue-700 bg-white p-5 shadow-sm transition hover:shadow-md hover:border-blue-800"
    >
      <div className="grid gap-4 md:grid-cols-[1fr_1fr_1fr_1.5fr] md:items-center">
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">
            Abertura {fmtDiaMes(data.abertura_data)}
          </div>
          <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
            {formatBRL(data.abertura_valor)}
          </div>
        </div>
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">
            Hoje {fmtDiaMes(data.hoje_data)}
          </div>
          <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">
            {formatBRL(data.hoje_valor)}
          </div>
        </div>
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Variação</div>
          <div className={`mt-1 text-lg font-semibold tabular-nums ${corVariacao}`}>
            {sinal}
            {formatBRL(data.variacao_valor)}
          </div>
          <div className={`text-xs tabular-nums ${corVariacao}`}>
            {sinal}
            {data.variacao_pct.toFixed(2)}%
          </div>
        </div>
        <div className="min-w-0">
          <Sparkline data={data.sparkline} />
        </div>
      </div>
    </a>
  )
}
