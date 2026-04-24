"use client"
import { useEffect, useState } from "react"
import Link from "next/link"
import { useFilters } from "@/lib/filters-context"
import {
  listarContratos,
  listarContratosAnteriores,
  listarContratosAnterioresFechadas,
} from "@/lib/api/contratos-competencia"
import { TabelaCidade } from "@/components/contratos/tabela-cidade"
import { CarryOverSection } from "@/components/contratos/carry-over-section"
import type { ContratoCidadeListItem, ContratoAnteriorItem } from "@/types/v2"
import { formatBRL } from "@/lib/format"
import { toast } from "sonner"

export default function ContratosPage() {
  const { competencia } = useFilters()
  const [itens, setItens] = useState<ContratoCidadeListItem[]>([])
  const [anteriores, setAnteriores] = useState<ContratoAnteriorItem[]>([])
  const [fechadas, setFechadas] = useState<ContratoAnteriorItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      listarContratos({ competencia }),
      listarContratosAnteriores(competencia),
      listarContratosAnterioresFechadas(competencia),
    ])
      .then(([atuais, ant, fec]) => {
        if (!cancelled) {
          setItens(atuais)
          setAnteriores(ant)
          setFechadas(fec)
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) toast.error("Falha: " + (e instanceof Error ? e.message : "erro"))
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [competencia])

  const saldoAtual = itens.reduce((s, i) => s + i.saldo, 0)
  const saldoAnteriores = anteriores.reduce((s, i) => s + i.saldo_aberto, 0)
  const totalGeral = saldoAtual + saldoAnteriores

  if (loading) return <div className="p-6 text-slate-500">Carregando contratos…</div>

  return (
    <div className="flex flex-col">
      <div className="bg-white px-5 pt-4 pb-2 flex items-center gap-2">
        <div className="w-1 h-4 bg-blue-600 rounded"></div>
        <h1 className="text-[13px] font-bold uppercase tracking-wide text-slate-900">
          Contratos de {formatCompetenciaCurta(competencia)}
        </h1>
        <span className="text-slate-500 text-xs">
          · {itens.length} contratos · {formatBRL(saldoAtual)} a pagar
        </span>
      </div>

      <TabelaCidade itens={itens} competencia={competencia} />
      <CarryOverSection itens={anteriores} />

      {fechadas.length > 0 && (
        <details className="mx-5 mt-3 bg-emerald-50 rounded border border-emerald-200">
          <summary className="px-3 py-2 cursor-pointer text-[13px] font-semibold text-emerald-800 hover:bg-emerald-100 flex items-center gap-2">
            <span className="text-base leading-none">✓</span>
            COMPETÊNCIAS ANTERIORES FECHADAS
            <span className="text-emerald-600 font-normal text-xs">
              · {fechadas.length} contrato(s) quitado(s) · {formatBRL(fechadas.reduce((s, i) => s + i.total_original, 0))}
            </span>
          </summary>
          <div className="px-3 pb-3 pt-2">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="text-[11px] uppercase tracking-wide text-emerald-700 border-b border-emerald-200">
                  <th className="text-left py-1.5">COMPET.</th>
                  <th className="text-left py-1.5">CONTRATO</th>
                  <th className="text-right py-1.5">PREST.</th>
                  <th className="text-right py-1.5">TOTAL</th>
                  <th className="text-right py-1.5">PAGO</th>
                  <th className="text-right py-1.5">STATUS</th>
                </tr>
              </thead>
              <tbody>
                {fechadas.map((c) => (
                  <tr key={`${c.competencia}-${c.contrato_id}`} className="border-b border-emerald-100 last:border-0 hover:bg-emerald-100/50">
                    <td className="py-1.5 font-mono">{formatCompetenciaCurta(c.competencia)}</td>
                    <td className="py-1.5 font-medium">
                      <Link
                        href={`/contratos/${c.contrato_id}/${c.competencia}`}
                        className="text-emerald-900 hover:underline"
                      >
                        {c.uf} - {c.cidade}
                      </Link>
                    </td>
                    <td className="py-1.5 text-right tabular-nums">{c.prestadores}</td>
                    <td className="py-1.5 text-right tabular-nums">{formatBRL(c.total_original)}</td>
                    <td className="py-1.5 text-right tabular-nums text-emerald-700">{formatBRL(c.total_pago)}</td>
                    <td className="py-1.5 text-right">
                      <span className="px-2 py-0.5 text-[10px] font-semibold uppercase rounded bg-emerald-200 text-emerald-900">
                        Quitado
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      <div className="px-5 py-3.5 bg-slate-900 text-white flex items-center gap-3 text-sm">
        <span className="text-slate-400 uppercase text-[11px] tracking-wide">Total em aberto</span>
        <span className="text-slate-400 text-[11px]">(atual + anteriores)</span>
        <span className="ml-auto text-lg font-bold tabular-nums">{formatBRL(totalGeral)}</span>
      </div>
    </div>
  )
}

function formatCompetenciaCurta(comp: string): string {
  const [y, m] = comp.split("-")
  return `${m}.${y.slice(2)}`
}
