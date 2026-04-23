"use client"

import { useState } from "react"
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

function labelMesAno(competencia: string): string {
  const m = /^(\d{4})-(\d{2})$/.exec(competencia)
  if (!m) return competencia
  const [, ano, mes] = m
  return `${MES_LABEL[mes] ?? mes}/${ano.slice(2)}`
}

function labelMesCurto(competencia: string): string {
  const m = /^\d{4}-(\d{2})$/.exec(competencia)
  return m ? MES_LABEL[m[1]] ?? competencia : competencia
}

function fmtAbrev(valor: number): string {
  const abs = Math.abs(valor)
  if (abs >= 1_000_000) return `R$ ${(valor / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `R$ ${Math.round(valor / 1_000)}k`
  return `R$ ${valor.toFixed(0)}`
}

export function DespesasPorTipo({ meses }: Props) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  if (meses.length < 2) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-2">
          Despesas por tipo
        </div>
        <div className="text-xs text-slate-500">dados insuficientes</div>
      </div>
    )
  }

  const W = 280
  const H = 70
  const padX = 8
  const padY = 6
  const totais = meses.map((m) => m.despesa_fixa + m.despesa_variavel + m.tributo)
  const maxV = Math.max(...totais) || 1
  const totalW = W - padX * 2
  const gap = 4
  const barW = (totalW - gap * (meses.length - 1)) / meses.length

  const hovered = hoveredIdx !== null ? meses[hoveredIdx] : null
  const hoveredTotal = hovered ? hovered.despesa_fixa + hovered.despesa_variavel + hovered.tributo : 0

  // Tooltip positioning: percent da largura do container
  const tooltipLeftPct =
    hoveredIdx !== null
      ? ((padX + hoveredIdx * (barW + gap) + barW / 2) / W) * 100
      : 0

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-2">
        Despesas por tipo
      </div>
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" preserveAspectRatio="none">
          {meses.map((m, i) => {
            const total = m.despesa_fixa + m.despesa_variavel + m.tributo
            const totalH = (total / maxV) * (H - padY * 2)
            const x = padX + i * (barW + gap)
            const baseY = H - padY
            const hVar = (m.despesa_variavel / (total || 1)) * totalH
            const hFix = (m.despesa_fixa / (total || 1)) * totalH
            const hTrib = (m.tributo / (total || 1)) * totalH
            const yVar = baseY - hVar
            const yFix = yVar - hFix
            const yTrib = yFix - hTrib
            return (
              <g
                key={i}
                onMouseEnter={() => setHoveredIdx(i)}
                onMouseLeave={() => setHoveredIdx(null)}
                style={{ cursor: "pointer" }}
              >
                {/* hitbox */}
                <rect
                  x={x - gap / 2}
                  y={padY}
                  width={barW + gap}
                  height={H - padY * 2}
                  fill="transparent"
                />
                <rect x={x} y={yVar} width={barW} height={hVar} fill="#dc2626" />
                <rect x={x} y={yFix} width={barW} height={hFix} fill="#f59e0b" />
                <rect x={x} y={yTrib} width={barW} height={hTrib} fill="#7c3aed" rx="1" />
              </g>
            )
          })}
        </svg>
        {hoveredIdx !== null && hovered && (
          <div
            className="absolute pointer-events-none bg-slate-900 text-white text-[10px] rounded px-2 py-1.5 shadow-lg z-10 whitespace-nowrap"
            style={{
              left: `${tooltipLeftPct}%`,
              top: 0,
              transform: "translate(-50%, -110%)",
            }}
          >
            <div className="font-bold mb-1 tabular-nums">
              {labelMesAno(hovered.competencia)} · {fmtAbrev(hoveredTotal)}
            </div>
            <div className="tabular-nums">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500 mr-1" />
              Variável — {fmtAbrev(hovered.despesa_variavel)} ·{" "}
              {hoveredTotal > 0 ? ((hovered.despesa_variavel / hoveredTotal) * 100).toFixed(0) : 0}%
            </div>
            <div className="tabular-nums">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 mr-1" />
              Fixa — {fmtAbrev(hovered.despesa_fixa)} ·{" "}
              {hoveredTotal > 0 ? ((hovered.despesa_fixa / hoveredTotal) * 100).toFixed(0) : 0}%
            </div>
            <div className="tabular-nums">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-violet-500 mr-1" />
              Tributo — {fmtAbrev(hovered.tributo)} ·{" "}
              {hoveredTotal > 0 ? ((hovered.tributo / hoveredTotal) * 100).toFixed(0) : 0}%
            </div>
          </div>
        )}
      </div>
      <div className="flex justify-between mt-1 px-1 text-[10px] text-slate-400 tabular-nums">
        {meses.map((m, i) => (
          <span key={i}>{labelMesCurto(m.competencia)}</span>
        ))}
      </div>
      <div className="flex items-center justify-between mt-2 text-[10px] text-slate-500">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-red-600" />
          Variável
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-500" />
          Fixa
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-violet-600" />
          Tributo
        </span>
      </div>
    </div>
  )
}
