"use client"
import { useCallback, useEffect, useState } from "react"
import { useFilters } from "@/lib/filters-context"
import {
  fetchDashboard,
  fetchEvolucaoCaixa,
  fetchCompromissos,
  fetchRecebiveis,
  fetchReceitaFinanceira,
} from "@/lib/api/dashboard"
import { fetchDashboardSaldos } from "@/lib/api/saldos"
import type {
  DashboardResponse,
  DashboardSaldos,
  EvolucaoCaixaResponse,
  CompromissosResponse,
  RecebiveisResponse,
  ReceitaFinanceiraResponse,
} from "@/types/v2"
import { KpisGrid } from "@/components/dashboard/kpis-grid"
import { AlertasList } from "@/components/dashboard/alertas-list"
import { LiquidezBanner } from "@/components/saldos/liquidez-banner"
import { ContasCorrentesSection } from "@/components/saldos/contas-correntes-section"
import { AplicacoesSection } from "@/components/saldos/aplicacoes-section"
import { EvolucaoCaixaCard } from "@/components/dashboard/evolucao-caixa-card"
import { ReceitaFinanceiraCard } from "@/components/dashboard/receita-financeira-card"
import { CompromissosCard } from "@/components/dashboard/compromissos-card"
import { RecebiveisCard } from "@/components/dashboard/recebiveis-card"
import { TendenciaGrid } from "@/components/dashboard/tendencia"
import { toast } from "sonner"

export default function DashboardPage() {
  const { empresa, competencia } = useFilters()
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [saldos, setSaldos] = useState<DashboardSaldos | null>(null)
  const [evolucao, setEvolucao] = useState<EvolucaoCaixaResponse | null>(null)
  const [compromissos, setCompromissos] = useState<CompromissosResponse | null>(null)
  const [recebiveis, setRecebiveis] = useState<RecebiveisResponse | null>(null)
  const [receita, setReceita] = useState<ReceitaFinanceiraResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const carregarSaldos = useCallback(async () => {
    try {
      const s = await fetchDashboardSaldos()
      setSaldos(s)
    } catch (err) {
      console.error(err)
      toast.error("Falha ao carregar saldos: " + (err instanceof Error ? err.message : "erro"))
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchDashboard({ competencia, empresa }),
      fetchDashboardSaldos(),
      fetchEvolucaoCaixa(competencia).catch(() => null),
      fetchCompromissos().catch(() => null),
      fetchRecebiveis().catch(() => null),
      fetchReceitaFinanceira(competencia).catch(() => null),
    ])
      .then(([d, s, ev, co, re, rf]) => {
        setData(d)
        setSaldos(s)
        setEvolucao(ev)
        setCompromissos(co)
        setRecebiveis(re)
        setReceita(rf)
      })
      .catch((err) => {
        console.error(err)
        toast.error("Falha ao carregar dashboard: " + (err instanceof Error ? err.message : "erro"))
      })
      .finally(() => setLoading(false))
  }, [empresa, competencia])

  if (loading) return <div className="p-6 text-slate-500">Carregando...</div>

  return (
    <div className="flex flex-col">
      {/* 1. Banner de liquidez + contas/aplicações */}
      {saldos && (
        <>
          <LiquidezBanner
            liquidezTotal={saldos.liquidez_total}
            disponivelAgora={saldos.disponivel_agora}
            reservaTravada={saldos.reserva_travada}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-slate-200">
            <ContasCorrentesSection contas={saldos.contas} onUpdated={carregarSaldos} />
            <AplicacoesSection aplicacoes={saldos.aplicacoes} onChanged={carregarSaldos} />
          </div>
        </>
      )}

      {/* 2. Corpo principal */}
      {data && (
        <div className="p-6 space-y-4">
          {/* 2a. Evolução do caixa */}
          {evolucao && <EvolucaoCaixaCard data={evolucao} />}

          {/* 2b. Pra onde foi o dinheiro (KPIs + link pra subpágina) */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h1 className="text-lg font-semibold text-slate-900">
                Pra onde foi o dinheiro · {formatCompetencia(data.competencia)}
              </h1>
              <a
                href="/dashboard/saidas"
                className="text-xs text-blue-700 hover:text-blue-900"
              >
                Ver detalhamento por bolso →
              </a>
            </div>
            <KpisGrid kpis={data.kpis} />
          </div>

          {/* 2c. Risco operacional */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {compromissos && <CompromissosCard data={compromissos} />}
            {recebiveis && <RecebiveisCard data={recebiveis} />}
          </div>

          {/* 2d. Receita financeira (card destacado) */}
          {receita && <ReceitaFinanceiraCard data={receita} />}

          {/* 2e. Tendência 6m (rodapé) */}
          <TendenciaGrid />

          {/* 2f. Alertas */}
          {data.alertas.length > 0 && (
            <div className="bg-white border border-red-200 rounded-lg p-4">
              <h2 className="text-xs font-semibold uppercase text-red-700 tracking-wide mb-3">
                ⚠ Alertas — {data.alertas.length} item(s)
              </h2>
              <AlertasList alertas={data.alertas} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function formatCompetencia(c: string): string {
  const [y, m] = c.split("-")
  const months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
  return `${months[parseInt(m, 10) - 1]}/${y}`
}
