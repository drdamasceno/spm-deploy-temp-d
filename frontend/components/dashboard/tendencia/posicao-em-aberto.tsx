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

export function PosicaoEmAberto({ meses }: Props) {
  if (meses.length < 2) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-2">
          Posição em aberto
        </div>
        <div className="text-xs text-slate-500">dados insuficientes</div>
      </div>
    )
  }

  const ultimo = meses[meses.length - 1]
  const aReceber = ultimo.recebiveis_atraso
  const aPagar = ultimo.compromissos_abertos
  const impacto = aReceber - aPagar
  const impactoPositivo = impacto >= 0

  const W = 280
  const H = 55
  const padX = 8
  const padY = 6
  const todosValores = meses.flatMap((m) => [m.compromissos_abertos, m.recebiveis_atraso])
  const minV = Math.min(...todosValores, 0)
  const maxV = Math.max(...todosValores)
  const range = maxV - minV || 1
  const stepX = (W - padX * 2) / (meses.length - 1)

  const pathPagar = meses
    .map((m, i) => {
      const x = padX + stepX * i
      const y = padY + (H - padY * 2) * (1 - (m.compromissos_abertos - minV) / range)
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(" ")

  const pathReceber = meses
    .map((m, i) => {
      const x = padX + stepX * i
      const y = padY + (H - padY * 2) * (1 - (m.recebiveis_atraso - minV) / range)
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(" ")

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-2">
        Posição em aberto
      </div>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-red-50 border-l-2 border-red-800 px-2 py-1.5 rounded-sm">
          <div className="text-[9px] text-slate-500 uppercase tracking-wide">A receber</div>
          <div className="text-xs font-bold text-red-900 tabular-nums">{fmtAbrev(aReceber)}</div>
        </div>
        <div className="bg-amber-50 border-l-2 border-amber-700 px-2 py-1.5 rounded-sm">
          <div className="text-[9px] text-slate-500 uppercase tracking-wide">A pagar</div>
          <div className="text-xs font-bold text-amber-900 tabular-nums">{fmtAbrev(aPagar)}</div>
        </div>
        <div className="bg-red-100 border-l-2 border-red-600 px-2 py-1.5 rounded-sm">
          <div className="text-[9px] text-slate-500 uppercase tracking-wide">Impacto caixa</div>
          <div
            className={`text-xs font-bold tabular-nums ${
              impactoPositivo ? "text-emerald-800" : "text-red-800"
            }`}
          >
            {impactoPositivo ? "+" : ""}
            {fmtAbrev(impacto)}
          </div>
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" preserveAspectRatio="none">
        <path d={pathPagar} fill="none" stroke="#b45309" strokeWidth="1.5" />
        <path
          d={pathReceber}
          fill="none"
          stroke="#991b1b"
          strokeWidth="1.5"
          strokeDasharray="4,3"
        />
      </svg>
      <div className="flex justify-between mt-1 px-1 text-[10px] text-slate-400 tabular-nums">
        {meses.map((m, i) => (
          <span key={i}>{labelMes(m.competencia)}</span>
        ))}
      </div>
      <div className="flex items-center justify-between mt-2 text-[10px] text-slate-500">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-amber-700" />
          Compromissos (a pagar)
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block w-3 h-0.5"
            style={{
              backgroundImage:
                "repeating-linear-gradient(to right, #991b1b 0 3px, transparent 3px 6px)",
            }}
          />
          Recebíveis (a receber)
        </span>
      </div>
    </div>
  )
}
