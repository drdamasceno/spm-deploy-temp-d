"use client"
import type { ContratoCidadeListItem } from "@/types/v2"
import type { MargemPorContrato } from "@/lib/api/margem"
import { formatBRL, formatDataBR } from "@/lib/format"
import Link from "next/link"

interface Props {
  itens: ContratoCidadeListItem[]
  competencia: string
  /** Mapa contrato_id → margem (do endpoint /margem/por-contrato).
   *  Quando ausente, coluna Margem mostra "—". */
  margemPorContratoId?: Record<string, MargemPorContrato>
  /** Callback ao clicar no botão de margem por profissional. */
  onAbrirMargem?: (contratoId: string, rotulo: string) => void
}

const STATUS_STYLE: Record<string, string> = {
  PAGO: "bg-emerald-100 text-emerald-800",
  PARCIAL: "bg-blue-100 text-blue-800",
  PENDENTE: "bg-amber-100 text-amber-800",
}

export function TabelaCidade({
  itens,
  competencia,
  margemPorContratoId,
  onAbrirMargem,
}: Props) {
  if (!itens.length) {
    return (
      <div className="p-6 text-sm text-slate-500 bg-white">
        Sem contratos em {competencia}.
      </div>
    )
  }
  const totalGeral = itens.reduce((s, i) => s + i.saldo, 0)
  const totalMargemReal = margemPorContratoId
    ? itens.reduce((s, i) => s + (margemPorContratoId[i.id]?.margem_realizado ?? 0), 0)
    : 0
  return (
    <div className="bg-white">
      <table className="w-full text-sm">
        <thead className="bg-slate-100 border-b-2 border-slate-300">
          <tr>
            <th className="px-3.5 py-2.5 text-left text-[11px] uppercase text-slate-600 font-semibold">Contrato</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Prest.</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Total</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Pago</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Saldo</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Margem</th>
            <th className="px-3.5 py-2.5 text-center text-[11px] uppercase text-slate-600 font-semibold">Status</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Data Pag.</th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {itens.map(it => {
            const margem = margemPorContratoId?.[it.id]
            const margemReal = margem?.margem_realizado ?? null
            const corMargem = margemReal !== null
              ? margemReal >= 0 ? "text-emerald-700" : "text-red-700"
              : "text-slate-400"
            const rotulo = `${it.uf}-${it.cidade}`
            return (
              <tr key={it.id} className="border-b border-slate-200 hover:bg-slate-50">
                <td className="px-3.5 py-2.5 font-semibold text-slate-900">
                  <Link href={`/contratos/${it.id}/${competencia}`} className="hover:underline">
                    {it.uf} - {it.cidade} - {formatCompetenciaCurta(it.competencia)}
                  </Link>
                </td>
                <td className="px-3.5 py-2.5 text-right text-slate-600">{it.prestadores}</td>
                <td className="px-3.5 py-2.5 text-right">{formatBRL(it.total)}</td>
                <td className="px-3.5 py-2.5 text-right text-slate-500">{formatBRL(it.total_pago)}</td>
                <td className="px-3.5 py-2.5 text-right font-semibold">{formatBRL(it.saldo)}</td>
                <td className={`px-3.5 py-2.5 text-right font-semibold ${corMargem}`}>
                  {margemReal !== null ? (
                    <button
                      type="button"
                      onClick={() => onAbrirMargem?.(it.id, rotulo)}
                      className="hover:underline"
                      title="Detalhar margem por profissional"
                    >
                      {formatBRL(margemReal)}
                      {margem?.margem_pct !== null && margem?.margem_pct !== undefined && (
                        <span className="text-[10px] font-normal opacity-80 ml-1">
                          ({(margem.margem_pct * 100).toFixed(1)}%)
                        </span>
                      )}
                    </button>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-3.5 py-2.5 text-center">
                  <span className={`inline-block text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${STATUS_STYLE[it.status]}`}>
                    {it.status[0] + it.status.slice(1).toLowerCase()}
                  </span>
                </td>
                <td className="px-3.5 py-2.5 text-right text-slate-600 tabular-nums text-xs">
                  {it.data_pagamento ? formatDataBR(it.data_pagamento) : "—"}
                </td>
              </tr>
            )
          })}
          <tr className="border-t-2 border-slate-300 bg-slate-50 font-bold">
            <td className="px-3.5 py-3">TOTAL · {itens.length} contratos</td>
            <td className="px-3.5 py-3 text-right">{itens.reduce((s, i) => s + i.prestadores, 0)}</td>
            <td className="px-3.5 py-3 text-right">{formatBRL(itens.reduce((s, i) => s + i.total, 0))}</td>
            <td className="px-3.5 py-3 text-right">{formatBRL(itens.reduce((s, i) => s + i.total_pago, 0))}</td>
            <td className="px-3.5 py-3 text-right text-red-900">{formatBRL(totalGeral)}</td>
            <td className={`px-3.5 py-3 text-right ${totalMargemReal >= 0 ? "text-emerald-700" : "text-red-700"}`}>
              {margemPorContratoId ? formatBRL(totalMargemReal) : "—"}
            </td>
            <td></td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function formatCompetenciaCurta(comp: string): string {
  const [y, m] = comp.split("-")
  return `${m}.${y.slice(2)}`
}
