"use client"
import { useEffect, useState } from "react"
import { useFilters } from "@/lib/filters-context"
import { fetchDashboard } from "@/lib/api/dashboard"
import type { DashboardResponse } from "@/types/v2"
import { DonutNaturezas } from "@/components/dashboard/donut-naturezas"
import { BarrasPxR } from "@/components/dashboard/barras-pxr"
import { formatBRL } from "@/lib/format"
import { toast } from "sonner"

/**
 * Stub da subpágina /dashboard/saidas.
 *
 * Objetivo desta fase (Track B Plano 02):
 * - Receber o tráfego que sai da home (onde os gráficos donut/barras
 *   deixaram de existir) e mostrar o detalhamento que vivia na home.
 * - Apresentar os 4 "bolsos" (SPM operacional, Via FD, Pessoal Hugo,
 *   Investimento Hugo) como agrupamento gerencial.
 *
 * Drill-down por bolso (lista de linhas individuais, por natureza, por
 * prestador) chega no Plano 03 (Fase D: UI de bolsos + split).
 */
export default function SaidasPage() {
  const { empresa, competencia } = useFilters()
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchDashboard({ competencia, empresa })
      .then(setData)
      .catch((err) => {
        toast.error(
          "Falha ao carregar saídas: " + (err instanceof Error ? err.message : "erro")
        )
      })
      .finally(() => setLoading(false))
  }, [empresa, competencia])

  if (loading) return <div className="p-6 text-slate-500">Carregando…</div>
  if (!data) return <div className="p-6 text-slate-500">Sem dados.</div>

  const total = data.kpis.saidas_mes

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
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <BolsoCard
          titulo="SPM operacional"
          cor="border-blue-700 bg-blue-50"
          descricao="Plantonistas, escritório, tributos SPM"
          valor={total}
          percent={100}
          nota="Filtro ainda não aplicado — drill-down por bolso chega no Plano 03"
        />
        <BolsoCard
          titulo="Via FD"
          cor="border-amber-600 bg-amber-50"
          descricao="Linhas com empresa_pagadora=FD (Thais, Vinicius, CLTs Unai/Itaju/Pedra Bela…)"
          valor={0}
          percent={0}
          nota="Valor populado após classificação pelo módulo de orçamento"
        />
        <BolsoCard
          titulo="Pessoal Hugo"
          cor="border-red-600 bg-red-50"
          descricao="Contas fixas, aluguéis, cartão metade. Contrapartida: mútuo SPM↔Hugo PF"
          valor={0}
          percent={0}
          nota="Valor populado após split de fatura de cartão (Plano 03)"
        />
        <BolsoCard
          titulo="Investimento Hugo"
          cor="border-violet-600 bg-violet-50"
          descricao="Terrenos Albatroz, Paysage, Odir. Contrapartida: mútuo SPM↔Hugo PF"
          valor={0}
          percent={0}
          nota="Valor populado após classificação pelo módulo de orçamento"
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
