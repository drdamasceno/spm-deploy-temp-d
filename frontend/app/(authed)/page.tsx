"use client"
import { useCallback, useEffect, useState } from "react"
import { useFilters } from "@/lib/filters-context"
import { fetchDashboard } from "@/lib/api/dashboard"
import { fetchDashboardSaldos } from "@/lib/api/saldos"
import type { DashboardResponse, DashboardSaldos } from "@/types/v2"
import { KpisGrid } from "@/components/dashboard/kpis-grid"
import { DonutNaturezas } from "@/components/dashboard/donut-naturezas"
import { BarrasPxR } from "@/components/dashboard/barras-pxr"
import { AlertasList } from "@/components/dashboard/alertas-list"
import { LiquidezBanner } from "@/components/saldos/liquidez-banner"
import { ContasCorrentesSection } from "@/components/saldos/contas-correntes-section"
import { AplicacoesSection } from "@/components/saldos/aplicacoes-section"
import { toast } from "sonner"

export default function DashboardPage() {
  const { empresa, competencia } = useFilters()
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [saldos, setSaldos] = useState<DashboardSaldos | null>(null)
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
    ])
      .then(([d, s]) => { setData(d); setSaldos(s) })
      .catch((err) => {
        console.error(err)
        toast.error("Falha ao carregar dashboard: " + (err instanceof Error ? err.message : "erro"))
      })
      .finally(() => setLoading(false))
  }, [empresa, competencia])

  if (loading) return <div className="p-6 text-slate-500">Carregando...</div>

  return (
    <div className="flex flex-col">
      {/* Banner de liquidez (novo — Track D) */}
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

      {/* Dashboard atual abaixo */}
      {data && (
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-semibold text-slate-900">
              Pra onde foi o dinheiro · {formatCompetencia(data.competencia)}
            </h1>
          </div>

          <KpisGrid kpis={data.kpis} />

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

          <div className="bg-white border border-red-200 rounded-lg p-4">
            <h2 className="text-xs font-semibold uppercase text-red-700 tracking-wide mb-3">
              ⚠ Alertas — {data.alertas.length} item(s)
            </h2>
            <AlertasList alertas={data.alertas} />
          </div>
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
