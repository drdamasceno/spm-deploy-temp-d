"use client"
import { useState, Fragment } from "react"
import type { ContratoAnteriorItem } from "@/types/v2"
import { formatBRL } from "@/lib/format"
import Link from "next/link"

interface Props {
  itens: ContratoAnteriorItem[]
}

export function CarryOverClosedSection({ itens }: Props) {
  const [open, setOpen] = useState(false)
  if (!itens.length) return null
  const totalPago = itens.reduce((s, i) => s + i.total_pago, 0)

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
          background: "linear-gradient(90deg,#ecfdf5 0%,#f8fafc 100%)",
          borderLeftColor: "#059669",
        }}
      >
        <span
          className="inline-block text-emerald-700 text-sm transition-transform"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >▶</span>
        <h3 className="m-0 text-[13px] text-emerald-900 font-bold uppercase tracking-wide">
          ✓ Competências anteriores fechadas
        </h3>
        <span className="text-emerald-700 text-xs">
          · {grupos.size} competência(s) · {itens.length} contratos quitados
        </span>
        <span className="ml-auto text-[15px] font-bold text-emerald-700 tabular-nums">
          {formatBRL(totalPago)}
        </span>
      </button>

      {open && (
        <div>
          <table className="w-full text-sm border-collapse">
            <thead className="bg-emerald-100 border-b border-emerald-300">
              <tr>
                <th className="px-3.5 py-2 text-left text-[10px] uppercase text-emerald-900">Compet.</th>
                <th className="px-3.5 py-2 text-left text-[10px] uppercase text-emerald-900">Contrato</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-emerald-900">Prest.</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-emerald-900">Saldo original</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-emerald-900">Pago</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-emerald-900">Saldo aberto</th>
                <th className="px-3.5 py-2 text-center text-[10px] uppercase text-emerald-900">Status</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {grupoOrdenado.map(([comp, itensGrupo]) => {
                const totalGrupoPago = itensGrupo.reduce((s, i) => s + i.total_pago, 0)
                return (
                  <Fragment key={comp}>
                    <tr style={{ background: "#d1fae5" }}>
                      <td colSpan={7} className="py-1.5 px-3.5 font-bold text-emerald-900 text-[12px]">
                        {formatCompetenciaCurta(comp)} · {itensGrupo.length} contrato(s) quitado(s) · pago {formatBRL(totalGrupoPago)}
                      </td>
                    </tr>
                    {itensGrupo.map(it => (
                      <tr
                        key={it.contrato_id + comp}
                        className="border-b border-slate-200 hover:bg-emerald-50"
                        style={{ background: "white" }}
                      >
                        <td className="px-3.5 py-2 text-xs text-slate-600">{formatCompetenciaCurta(comp)}</td>
                        <td className="px-3.5 py-2 font-semibold text-slate-900">
                          <Link href={`/contratos/${it.contrato_id}/${comp}`} className="hover:underline">
                            {it.uf} - {it.cidade}
                          </Link>
                        </td>
                        <td className="px-3.5 py-2 text-right text-slate-600">{it.prestadores}</td>
                        <td className="px-3.5 py-2 text-right text-slate-500">{formatBRL(it.total_original)}</td>
                        <td className="px-3.5 py-2 text-right text-emerald-700">{formatBRL(it.total_pago)}</td>
                        <td className="px-3.5 py-2 text-right font-bold text-emerald-700">R$ 0,00</td>
                        <td className="px-3.5 py-2 text-center">
                          <span className="inline-block text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-200 text-emerald-900">
                            Quitado
                          </span>
                        </td>
                      </tr>
                    ))}
                  </Fragment>
                )
              })}
              <tr className="border-t-2 border-emerald-300 bg-emerald-100 font-bold">
                <td colSpan={4} className="px-3.5 py-2.5 text-emerald-900">Total quitado (competências fechadas)</td>
                <td className="px-3.5 py-2.5 text-right text-emerald-700 tabular-nums">{formatBRL(totalPago)}</td>
                <td className="px-3.5 py-2.5 text-right text-emerald-700 tabular-nums">R$ 0,00</td>
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
