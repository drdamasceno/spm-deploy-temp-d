"use client"
import type { ContratoCidadeListItem } from "@/types/v2"
import { formatBRL, formatDataBR } from "@/lib/format"
import Link from "next/link"

interface Props {
  itens: ContratoCidadeListItem[]
  competencia: string
}

const STATUS_STYLE: Record<string, string> = {
  PAGO: "bg-emerald-100 text-emerald-800",
  PARCIAL: "bg-blue-100 text-blue-800",
  PENDENTE: "bg-amber-100 text-amber-800",
}

export function TabelaCidade({ itens, competencia }: Props) {
  if (!itens.length) {
    return (
      <div className="p-6 text-sm text-slate-500 bg-white">
        Sem contratos em {competencia}.
      </div>
    )
  }
  const totalGeral = itens.reduce((s, i) => s + i.saldo, 0)
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
            <th className="px-3.5 py-2.5 text-center text-[11px] uppercase text-slate-600 font-semibold">Status</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Data Pag.</th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {itens.map(it => (
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
              <td className="px-3.5 py-2.5 text-center">
                <span className={`inline-block text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${STATUS_STYLE[it.status]}`}>
                  {it.status[0] + it.status.slice(1).toLowerCase()}
                </span>
              </td>
              <td className="px-3.5 py-2.5 text-right text-slate-600 tabular-nums text-xs">
                {it.data_pagamento ? formatDataBR(it.data_pagamento) : "—"}
              </td>
            </tr>
          ))}
          <tr className="border-t-2 border-slate-300 bg-slate-50 font-bold">
            <td className="px-3.5 py-3">TOTAL · {itens.length} contratos</td>
            <td className="px-3.5 py-3 text-right">{itens.reduce((s, i) => s + i.prestadores, 0)}</td>
            <td className="px-3.5 py-3 text-right">{formatBRL(itens.reduce((s, i) => s + i.total, 0))}</td>
            <td className="px-3.5 py-3 text-right">{formatBRL(itens.reduce((s, i) => s + i.total_pago, 0))}</td>
            <td className="px-3.5 py-3 text-right text-red-900">{formatBRL(totalGeral)}</td>
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
