"use client"
import { useEffect, useState } from "react"
import { useFilters } from "@/lib/filters-context"
import {
  listarContratos,
  listarContratosAnteriores,
  listarContratosAnterioresFechadas,
} from "@/lib/api/contratos-competencia"
import { TabelaCidade } from "@/components/contratos/tabela-cidade"
import { CarryOverSection } from "@/components/contratos/carry-over-section"
import { CarryOverClosedSection } from "@/components/contratos/carry-over-closed-section"
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

      <CarryOverClosedSection itens={fechadas} />

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
