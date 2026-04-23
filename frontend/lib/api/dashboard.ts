// frontend/lib/api/dashboard.ts
import { apiClient } from "@/lib/api"
import type {
  CompromissosResponse,
  DashboardResponse,
  EmpresaCodigo,
  EvolucaoCaixaResponse,
  HistoricoResponse,
  ReceitaFinanceiraResponse,
  RecebiveisResponse,
  SaidasPorBolsoResponse,
} from "@/types/v2"

export interface FetchDashboardParams {
  competencia: string
  empresa: EmpresaCodigo
}

export async function fetchDashboard(
  params: FetchDashboardParams
): Promise<DashboardResponse> {
  const { data } = await apiClient.get<DashboardResponse>("/dashboard", { params })
  return data
}

// ─── Dashboard v2 (Track B — Plano 02) ───────────────────────────────────

export async function fetchEvolucaoCaixa(
  competencia: string
): Promise<EvolucaoCaixaResponse> {
  const { data } = await apiClient.get<EvolucaoCaixaResponse>(
    "/dashboard/evolucao-caixa",
    { params: { competencia } }
  )
  return data
}

export async function fetchCompromissos(): Promise<CompromissosResponse> {
  const { data } = await apiClient.get<CompromissosResponse>("/dashboard/compromissos")
  return data
}

export async function fetchRecebiveis(): Promise<RecebiveisResponse> {
  const { data } = await apiClient.get<RecebiveisResponse>("/dashboard/recebiveis")
  return data
}

export async function fetchReceitaFinanceira(
  competencia: string
): Promise<ReceitaFinanceiraResponse> {
  const { data } = await apiClient.get<ReceitaFinanceiraResponse>(
    "/dashboard/receita-financeira",
    { params: { competencia } }
  )
  return data
}

export async function fetchHistorico(
  meses: number = 6
): Promise<HistoricoResponse> {
  const { data } = await apiClient.get<HistoricoResponse>(
    "/dashboard/historico",
    { params: { meses } }
  )
  return data
}

export async function fetchSaidasPorBolso(
  competencia: string
): Promise<SaidasPorBolsoResponse> {
  const { data } = await apiClient.get<SaidasPorBolsoResponse>(
    "/dashboard/saidas-por-bolso",
    { params: { competencia } }
  )
  return data
}
