"use client"

import type { MesHistorico } from "@/types/v2"

interface Props {
  meses: MesHistorico[]
}

const MES_LABEL: Record<string, string> = {
  "01": "Jan",
  "02": "Fev",
  "03": "Mar",
  "04": "Abr",
  "05": "Mai",
  "06": "Jun",
  "07": "Jul",
  "08": "Ago",
  "09": "Set",
  "10": "Out",
  "11": "Nov",
  "12": "Dez",
}

function labelMes(competencia: string): string {
  const m = /^\d{4}-(\d{2})$/.exec(competencia)
  return m ? MES_LABEL[m[1]] ?? competencia : competencia
}

function fmtAbrev(valor: number): string {
  const abs = Math.abs(valor)
  if (abs >= 1_000_000) return `R$ ${(valor / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `R$ ${Math.round(valor / 1_000)}k`
  return `R$ ${valor.toFixed(0)}`
}

export function Faturamento({ meses }: Props) {
  if (meses.length < 2) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-2">
          Faturamento
        </div>
        <div className="text-xs text-slate-500">dados insuficientes</div>
      </div>
    )
  }

  const W = 280
  const H = 70
  const padX = 8
  const padY = 6
  const valores = meses.map((m) => m.faturamento)
  const minV = Math.min(...valores, 0)
  const maxV = Math.max(...valores)
  const range = maxV - minV || 1
  const totalW = W - padX * 2
  const gap = 4
  const barW = (totalW - gap * (meses.length - 1)) / meses.length

  const media = valores.reduce((s, v) => s + v, 0) / valores.length
  const atual = valores[valores.length - 1]
  const delta = media === 0 ? 0 : ((atual - media) / Math.abs(media)) * 100
  const positivo = delta >= 0
  const deltaLabel = `${positivo ? "+" : ""}${delta.toFixed(1)}% vs média`
  const deltaCor = positivo ? "text-emerald-700 bg-emerald-50" : "text-red-700 bg-red-50"

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-2">
        <div className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
          Faturamento
        </div>
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded tabular-nums ${deltaCor}`}>
          {deltaLabel}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" preserveAspectRatio="none">
        {meses.map((m, i) => {
          const h = ((m.faturamento - minV) / range) * (H - padY * 2)
          const x = padX + i * (barW + gap)
          const y = H - padY - h
          const ultimo = i === meses.length - 1
          return (
            <rect
              key={i}
              x={x}
              y={y}
              width={barW}
              height={h}
              fill={ultimo ? "#15803d" : "#16a34a"}
              rx="1"
            />
          )
        })}
      </svg>
      <div className="flex justify-between mt-1 px-1 text-[10px] text-slate-400 tabular-nums">
        {meses.map((m, i) => (
          <span key={i}>{labelMes(m.competencia)}</span>
        ))}
      </div>
      <div className="flex items-center justify-between mt-2 text-xs">
        <span className="text-slate-500 tabular-nums">Média 6m: {fmtAbrev(media)}</span>
        <span className="font-bold text-emerald-700 tabular-nums">
          Mês atual: {fmtAbrev(atual)}
        </span>
      </div>
    </div>
  )
}
