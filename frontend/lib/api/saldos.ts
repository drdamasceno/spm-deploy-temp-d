import { apiClient } from "@/lib/api"
import type {
  DashboardSaldos,
  AplicacaoOut,
  AplicacaoCreate,
  AplicacaoPatch,
  SaldoManualInput,
} from "@/types/v2"

export async function fetchDashboardSaldos(): Promise<DashboardSaldos> {
  const { data } = await apiClient.get<DashboardSaldos>("/saldos/dashboard")
  return data
}

export async function registrarSaldoManual(payload: SaldoManualInput): Promise<{ id: string }> {
  const { data } = await apiClient.post<{ id: string }>("/saldos/conta-manual", payload)
  return data
}

export async function listarAplicacoes(): Promise<AplicacaoOut[]> {
  const { data } = await apiClient.get<AplicacaoOut[]>("/aplicacoes")
  return data
}

export async function criarAplicacao(payload: AplicacaoCreate): Promise<AplicacaoOut> {
  const { data } = await apiClient.post<AplicacaoOut>("/aplicacoes", payload)
  return data
}

export async function editarAplicacao(id: string, patch: AplicacaoPatch): Promise<AplicacaoOut> {
  const { data } = await apiClient.patch<AplicacaoOut>(`/aplicacoes/${id}`, patch)
  return data
}

export async function deletarAplicacao(id: string): Promise<void> {
  await apiClient.delete(`/aplicacoes/${id}`)
}
