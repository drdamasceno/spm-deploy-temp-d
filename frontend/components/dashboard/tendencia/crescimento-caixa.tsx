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

export function CrescimentoCaixa({ meses }: Props) {
  if (meses.length < 2) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-2">
          Crescimento de caixa
        </div>
        <div className="text-xs text-slate-500">dados insuficientes</div>
      </div>
    )
  }

  const W = 280
  const H = 70
  const padX = 8
  const padY = 10
  const valores = meses.map((m) => m.liquidez)
  const minV = Math.min(...valores)
  const maxV = Math.max(...valores)
  const range = maxV - minV || 1
  const stepX = (W - padX * 2) / (meses.length - 1)

  const points = meses.map((m, i) => {
    const x = padX + stepX * i
    const y = padY + (H - padY * 2) * (1 - (m.liquidez - minV) / range)
    return { x, y, v: m.liquidez, label: labelMes(m.competencia) }
  })

  const linhaPath = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ")
  const areaPath = `${linhaPath} L${points[points.length - 1].x.toFixed(2)},${H - padY / 2} L${points[0].x.toFixed(2)},${H - padY / 2} Z`

  const primeiro = meses[0]
  const ultimo = meses[meses.length - 1]
  const delta = primeiro.liquidez === 0 ? 0 : ((ultimo.liquidez - primeiro.liquidez) / Math.abs(primeiro.liquidez)) * 100
  const positivo = delta >= 0
  const deltaLabel = `${positivo ? "+" : ""}${delta.toFixed(1)}%`
  const deltaCor = positivo ? "text-emerald-700 bg-emerald-50" : "text-red-700 bg-red-50"

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-2">
        <div className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
          Crescimento de caixa
        </div>
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded tabular-nums ${deltaCor}`}>
          {deltaLabel}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" preserveAspectRatio="none">
        <defs>
          <linearGradient id="grad-caixa" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1e40af" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#1e40af" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#grad-caixa)" />
        <path d={linhaPath} fill="none" stroke="#1e40af" strokeWidth="1.5" />
        {points.map((p, i) => {
          const ultimoPonto = i === points.length - 1
          return (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={ultimoPonto ? 3 : 2}
              fill={ultimoPonto ? "#1e40af" : "#ffffff"}
              stroke="#1e40af"
              strokeWidth="1.2"
            />
          )
        })}
      </svg>
      <div className="flex justify-between mt-1 px-1 text-[10px] text-slate-400 tabular-nums">
        {points.map((p, i) => (
          <span key={i}>{p.label}</span>
        ))}
      </div>
      <div className="flex items-center justify-between mt-2 text-xs">
        <span className="text-slate-500 tabular-nums">
          {labelMes(primeiro.competencia)}: {fmtAbrev(primeiro.liquidez)}
        </span>
        <span className="font-bold text-emerald-700 tabular-nums">
          {labelMes(ultimo.competencia)}: {fmtAbrev(ultimo.liquidez)}
        </span>
      </div>
    </div>
  )
}
