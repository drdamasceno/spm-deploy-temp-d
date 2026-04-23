"use client"
import { useEffect, useState } from "react"
import { useFilters } from "@/lib/filters-context"
import { fetchDashboard, fetchSaidasPorBolso } from "@/lib/api/dashboard"
import type { DashboardResponse, SaidasPorBolsoResponse } from "@/types/v2"
import { DonutNaturezas } from "@/components/dashboard/donut-naturezas"
import { BarrasPxR } from "@/components/dashboard/barras-pxr"
import { formatBRL } from "@/lib/format"
import { toast } from "sonner"

/**
 * Subpágina /dashboard/saidas — drill-down por bolso.
 *
 * Fonte dos bolsos: /dashboard/saidas-por-bolso agrega transacao_bancaria
 * DEBITO do mês. Transação COM split usa as linhas filhas; transação SEM
 * split cai toda em SPM_OPERACIONAL (fallback).
 *
 * Conforme Hugo classifica com split (tela /transacoes/[id]/split) ou com
 * empresa_pagadora nas linhas do orçamento, os valores dos bolsos
 * FD_VIA_SPM / HUGO_PESSOAL / INVESTIMENTO_HUGO saem de zero.
 */
export default function SaidasPage() {
  const { empresa, competencia } = useFilters()
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [bolsos, setBolsos] = useState<SaidasPorBolsoResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchDashboard({ competencia, empresa }),
      fetchSaidasPorBolso(competencia).catch(() => null),
    ])
      .then(([d, b]) => {
        setData(d)
        setBolsos(b)
      })
      .catch((err) => {
        toast.error(
          "Falha ao carregar saídas: " + (err instanceof Error ? err.message : "erro")
        )
      })
      .finally(() => setLoading(false))
  }, [empresa, competencia])

  if (loading) return <div className="p-6 text-slate-500">Carregando…</div>
  if (!data) return <div className="p-6 text-slate-500">Sem dados.</div>

  const total = bolsos?.total ?? data.kpis.saidas_mes
  const pct = (v: number) => (total > 0 ? (v / total) * 100 : 0)

  return (
    <div className="p-6 space-y-5">
      <div>
        <a href="/" className="text-xs text-slate-500 hover:text-slate-900">
          ← Voltar
        </a>
        <h1 className="mt-1 text-lg font-semibold text-slate-900">
          Saídas de {formatCompetencia(data.competencia)}
        </h1>
        <div className="text-sm text-slate-500 mt-1">
          Total: <span className="font-semibold text-slate-900">{formatBRL(total)}</span> em 4 bolsos
          {bolsos && (
            <span className="ml-2 text-xs text-slate-400">
              · {bolsos.com_split_count} de {bolsos.transacoes_count} transações já com split
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <BolsoCard
          titulo="SPM operacional"
          cor="border-blue-700 bg-blue-50"
          descricao="Plantonistas, escritório, tributos SPM"
          valor={bolsos?.spm_operacional ?? total}
          percent={pct(bolsos?.spm_operacional ?? total)}
          nota={
            bolsos && bolsos.com_split_count < bolsos.transacoes_count
              ? `Inclui ${bolsos.transacoes_count - bolsos.com_split_count} transações ainda não classificadas por split`
              : undefined
          }
        />
        <BolsoCard
          titulo="Via FD"
          cor="border-amber-600 bg-amber-50"
          descricao="Linhas de transação com bolso=FD_VIA_SPM (Thais, Vinicius, CLTs Unai/Itaju/Pedra Bela…)"
          valor={bolsos?.fd_via_spm ?? 0}
          percent={pct(bolsos?.fd_via_spm ?? 0)}
          nota="Popula conforme Hugo classifica splits ou edita orcamento_linha.empresa_pagadora=FD"
        />
        <BolsoCard
          titulo="Pessoal Hugo"
          cor="border-red-600 bg-red-50"
          descricao="Contas fixas, aluguéis, cartão metade. Contrapartida: mútuo SPM↔Hugo PF"
          valor={bolsos?.hugo_pessoal ?? 0}
          percent={pct(bolsos?.hugo_pessoal ?? 0)}
          nota="Popula conforme Hugo divide fatura de cartão em /transacoes/[id]/split"
        />
        <BolsoCard
          titulo="Investimento Hugo"
          cor="border-violet-600 bg-violet-50"
          descricao="Terrenos Albatroz, Paysage, Odir. Contrapartida: mútuo SPM↔Hugo PF"
          valor={bolsos?.investimento_hugo ?? 0}
          percent={pct(bolsos?.investimento_hugo ?? 0)}
          nota="Popula conforme Hugo classifica transações de compra/aporte em investimento"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.5fr] gap-3">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <h2 className="text-xs font-semibold uppercase text-slate-600 tracking-wide mb-3">
            Saídas por natureza
          </h2>
          <DonutNaturezas saidas={data.saidas_por_natureza} />
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <h2 className="text-xs font-semibold uppercase text-slate-600 tracking-wide mb-3">
            Previsto × Realizado por categoria
          </h2>
          <BarrasPxR barras={data.previsto_x_realizado} />
        </div>
      </div>
    </div>
  )
}

interface BolsoCardProps {
  titulo: string
  cor: string
  descricao: string
  valor: number
  percent: number
  nota?: string
}

function BolsoCard({ titulo, cor, descricao, valor, percent, nota }: BolsoCardProps) {
  return (
    <div className={`rounded-lg border-2 p-4 ${cor}`}>
      <div className="flex items-baseline justify-between">
        <div className="text-xs font-bold uppercase tracking-wide text-slate-800">{titulo}</div>
        <div className="text-xs text-slate-500">{percent.toFixed(1)}% do total</div>
      </div>
      <div className="mt-2 text-xl font-bold tabular-nums text-slate-900">{formatBRL(valor)}</div>
      <div className="mt-1 text-xs text-slate-600">{descricao}</div>
      {nota && <div className="mt-2 text-[10px] italic text-slate-500">{nota}</div>}
    </div>
  )
}

function formatCompetencia(c: string): string {
  const [y, m] = c.split("-")
  const meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
  return `${meses[parseInt(m, 10) - 1]}/${y}`
}
