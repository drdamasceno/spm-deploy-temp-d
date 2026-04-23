"use client"

import { formatBRL } from "@/lib/format"
import type { CompromissosResponse } from "@/types/v2"

interface CompromissosCardProps {
  data: CompromissosResponse
}

export function CompromissosCard({ data }: CompromissosCardProps) {
  const pp = data.por_fonte?.["PP"] ?? 0
  const faturas = data.por_fonte?.["FATURAS"] ?? 0
  return (
    <a
      href="/dashboard/compromissos"
      className="block rounded-xl border border-amber-300 bg-amber-50 p-5 shadow-sm transition hover:shadow-md hover:border-amber-400"
    >
      <div className="text-xs font-bold uppercase tracking-wide text-amber-800">
        ⏳ Compromissos em aberto
      </div>
      <div className="mt-2 text-2xl font-bold tabular-nums text-slate-900">
        {formatBRL(data.total)}
      </div>
      <div className="mt-1 text-xs text-slate-500">
        PP {formatBRL(pp)} · Faturas {formatBRL(faturas)} →
      </div>
    </a>
  )
}
