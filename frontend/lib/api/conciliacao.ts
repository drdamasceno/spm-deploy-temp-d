// frontend/lib/api/conciliacao.ts
import { apiClient } from "@/lib/api"
import type { ConciliacaoCreate, SugestaoOut } from "@/types/v2"

export interface FetchSugestoesParams {
  orcamento_id: string
  conta_id?: string
}

export async function fetchSugestoes(
  params: FetchSugestoesParams
): Promise<SugestaoOut[]> {
  const { data } = await apiClient.get<SugestaoOut[]>("/conciliacoes/sugestoes", {
    params,
  })
  return data
}

export async function aplicarConciliacao(
  payload: ConciliacaoCreate
): Promise<ConciliacaoCreate> {
  const { data } = await apiClient.post<ConciliacaoCreate>("/conciliacoes", payload)
  return data
}

export async function deletarConciliacao(id: string): Promise<void> {
  await apiClient.delete(`/conciliacoes/${id}`)
}

export interface TransacaoDetalhe {
  id: string
  titular_pix: string | null
  valor: number
  data_extrato: string
  origem_banco: string
}

export interface OrcamentoLinhaDetalhe {
  id: string
  titular_razao_social: string
  valor_previsto: number
  natureza: string
  observacao: string | null
}

export interface LookupDetalhesResponse {
  transacoes: TransacaoDetalhe[]
  orcamento_linhas: OrcamentoLinhaDetalhe[]
}

export interface LookupDetalhesParams {
  transacao_ids: string[]
  orcamento_linha_ids: string[]
}

export async function lookupDetalhes(
  params: LookupDetalhesParams
): Promise<LookupDetalhesResponse> {
  const { data } = await apiClient.post<LookupDetalhesResponse>(
    "/conciliacoes/sugestoes/lookup",
    params
  )
  return data
}
