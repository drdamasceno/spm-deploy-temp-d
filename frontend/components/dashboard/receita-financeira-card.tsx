"use client"

import { formatBRL } from "@/lib/format"
import type { ReceitaFinanceiraResponse } from "@/types/v2"

interface ReceitaFinanceiraCardProps {
  data: ReceitaFinanceiraResponse
}

export function ReceitaFinanceiraCard({ data }: ReceitaFinanceiraCardProps) {
  return (
    <a
      href="/dashboard/receita-financeira"
      className="block rounded-xl border-2 border-violet-600 bg-gradient-to-br from-violet-50 to-violet-100 p-5 shadow-sm transition hover:shadow-md hover:border-violet-700"
    >
      <div className="grid gap-4 md:grid-cols-[2fr_1fr_1fr] md:items-center">
        <div>
          <div className="text-xs font-medium text-violet-700 uppercase tracking-wide">
            Rendimento do mês
          </div>
          <div className="mt-1 text-3xl font-bold tabular-nums text-violet-700">
            {formatBRL(data.rendimento_mes)}
          </div>
          <div className="mt-1 text-xs text-slate-600">Bradesco CDB + rendimentos CC</div>
        </div>
        <div>
          <div className="text-xs font-medium text-violet-700 uppercase tracking-wide">Acum. 2026</div>
          <div className="mt-1 text-base font-semibold tabular-nums text-slate-900">
            {formatBRL(data.acumulado_ano)}
          </div>
        </div>
        <div>
          <div className="text-xs font-medium text-violet-700 uppercase tracking-wide">Rentab. mês</div>
          <div className="mt-1 text-base font-semibold tabular-nums text-slate-900">
            {data.rentabilidade_pct.toFixed(2)}%
          </div>
          <div className="text-xs text-slate-600">≈ {data.percent_cdi.toFixed(0)}% CDI</div>
        </div>
      </div>
    </a>
  )
}
