"use client"
import { useState, Fragment } from "react"
import type { ContratoAnteriorItem } from "@/types/v2"
import { formatBRL, formatDataBR } from "@/lib/format"
import Link from "next/link"

interface Props {
  itens: ContratoAnteriorItem[]
}

function ageClass(dias: number): {
  bgFrom: string; bgTo: string; border: string; text: string; icon?: string; caps?: string
} {
  if (dias >= 90) return {
    bgFrom: "#fca5a5", bgTo: "#fecaca",
    border: "#dc2626", text: "#7f1d1d",
    icon: "⚠️", caps: "URGENTE",
  }
  if (dias >= 60) return {
    bgFrom: "#fed7aa", bgTo: "#fef3c7",
    border: "#ea580c", text: "#9a3412",
    icon: "⏱",
  }
  return {
    bgFrom: "#e0e7ff", bgTo: "#e0e7ff",
    border: "#4f46e5", text: "#312e81",
  }
}

export function CarryOverSection({ itens }: Props) {
  const [open, setOpen] = useState(false)
  if (!itens.length) return null
  const totalSaldo = itens.reduce((s, i) => s + i.saldo_aberto, 0)

  const grupos = new Map<string, ContratoAnteriorItem[]>()
  for (const i of itens) {
    if (!grupos.has(i.competencia)) grupos.set(i.competencia, [])
    grupos.get(i.competencia)!.push(i)
  }
  const grupoOrdenado = [...grupos.entries()].sort(([a], [b]) => b.localeCompare(a))

  return (
    <div className="mt-5 border-t border-slate-200">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full px-5 py-3.5 flex items-center gap-2.5 cursor-pointer select-none hover:brightness-95 transition-all border-l-4"
        style={{
          background: "linear-gradient(90deg,#eef2ff 0%,#f8fafc 100%)",
          borderLeftColor: "#4f46e5",
        }}
      >
        <span
          className="inline-block text-indigo-700 text-sm transition-transform"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >▶</span>
        <h3 className="m-0 text-[13px] text-indigo-900 font-bold uppercase tracking-wide">
          Competências anteriores em aberto
        </h3>
        <span className="text-indigo-700 text-xs">
          · {grupos.size} competências · {itens.length} contratos
        </span>
        <span className="ml-auto text-[15px] font-bold text-indigo-700 tabular-nums">
          {formatBRL(totalSaldo)}
        </span>
      </button>

      {open && (
        <div>
          <table className="w-full text-sm border-collapse">
            <thead className="bg-indigo-100 border-b border-indigo-300">
              <tr>
                <th className="px-3.5 py-2 text-left text-[10px] uppercase text-indigo-900">Compet.</th>
                <th className="px-3.5 py-2 text-left text-[10px] uppercase text-indigo-900">Contrato</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-indigo-900">Prest.</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-indigo-900">Saldo original</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-indigo-900">Pago</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-indigo-900">Saldo aberto</th>
                <th className="px-3.5 py-2 text-center text-[10px] uppercase text-indigo-900">Status</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-indigo-900">Data Pag.</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {grupoOrdenado.map(([comp, itensGrupo]) => {
                const dias = Math.max(...itensGrupo.map(i => i.idade_dias))
                const style = ageClass(dias)
                const saldoGrupo = itensGrupo.reduce((s, i) => s + i.saldo_aberto, 0)
                const isDestaque = dias >= 60
                return (
                  <Fragment key={comp}>
                    <tr
                      style={isDestaque
                        ? { background: `linear-gradient(90deg,${style.bgFrom} 0%,${style.bgTo} 100%)`, borderTop: `${dias >= 90 ? 3 : 2}px solid ${style.border}` }
                        : { background: "#e0e7ff" }}>
                      <td colSpan={8} className={`${isDestaque ? "py-2.5" : "py-1.5"} px-3.5 font-bold`}
                        style={{ color: style.text, fontSize: isDestaque ? 13 : 12 }}>
                        {style.icon && <span className="mr-1.5" style={{ fontSize: dias >= 90 ? 16 : 14 }}>{style.icon}</span>}
                        {formatCompetenciaCurta(comp)} ·
                        <span style={{ fontSize: dias >= 90 ? 16 : isDestaque ? 14 : undefined }}>
                          {" "}{dias} dias em aberto{style.caps ? " — " + style.caps : ""}
                        </span>
                        {" "}· saldo {formatBRL(saldoGrupo)}
                        {dias >= 90 && <span className="ml-2.5 inline-block text-[10px] px-2.5 py-0.5 bg-red-900 text-white rounded-full font-bold">90+ DIAS</span>}
                      </td>
                    </tr>
                    {itensGrupo.map(it => (
                      <tr key={it.contrato_id + comp} className="border-b border-slate-200"
                        style={isDestaque ? { background: dias >= 90 ? "#fef2f2" : "#fff7ed" } : { background: "white" }}>
                        <td className="px-3.5 py-2 text-xs text-slate-600">{formatCompetenciaCurta(comp)}</td>
                        <td className="px-3.5 py-2 font-semibold text-slate-900">
                          <Link href={`/contratos/${it.contrato_id}/${comp}`} className="hover:underline">
                            {it.uf} - {it.cidade}
                          </Link>
                        </td>
                        <td className="px-3.5 py-2 text-right text-slate-600">{it.prestadores}</td>
                        <td className="px-3.5 py-2 text-right text-slate-500">{formatBRL(it.total_original)}</td>
                        <td className="px-3.5 py-2 text-right text-blue-800">{formatBRL(it.total_pago)}</td>
                        <td className="px-3.5 py-2 text-right font-bold text-red-900">{formatBRL(it.saldo_aberto)}</td>
                        <td className="px-3.5 py-2 text-center">
                          <span className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                            {it.status[0] + it.status.slice(1).toLowerCase()}
                          </span>
                        </td>
                        <td className="px-3.5 py-2 text-right text-slate-600 tabular-nums text-xs">
                          {it.data_pagamento ? formatDataBR(it.data_pagamento) : "—"}
                        </td>
                      </tr>
                    ))}
                  </Fragment>
                )
              })}
              <tr className="border-t-2 border-indigo-300 bg-indigo-100 font-bold">
                <td colSpan={5} className="px-3.5 py-2.5 text-indigo-900">Total em aberto (residual)</td>
                <td className="px-3.5 py-2.5 text-right text-indigo-700 tabular-nums">{formatBRL(totalSaldo)}</td>
                <td></td>
                <td></td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function formatCompetenciaCurta(comp: string): string {
  const [y, m] = comp.split("-")
  return `${m}.${y.slice(2)}`
}
