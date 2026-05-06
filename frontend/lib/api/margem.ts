// frontend/lib/api/margem.ts
// API client para os endpoints /margem/* e /orcamentos/{id}/realizado-por-linha.
// Estes endpoints fornecem (a) realizado por linha de orçamento (heurística +
// CNAB-240), (b) margem por contrato e (c) margem por profissional dentro
// de um contrato/competência.
import { apiClient } from "@/lib/api"

export interface RealizadoPorLinha {
  linha_id: string
  pago: number
  data_max: string | null
  txs_count: number
  pago_cnab: number
  data_max_cnab: string | null
  retornos_count: number
}

export interface MargemPorContrato {
  contrato_id: string | null
  rotulo: string
  faturamento_previsto: number
  faturamento_realizado: number
  despesa_prof_previsto: number
  despesa_prof_realizado: number
  margem_previsto: number
  margem_realizado: number
  margem_pct: number | null
}

export interface MargemPorProfissional {
  prestador_id: string
  prestador_nome: string
  bonificacao: number
  share: number
  receita_atribuida: number
  margem_absoluta: number
  margem_pct: number | null
  pix_confirmado: number
  data_ultimo_pix: string | null
}

export interface ConciliacaoDetalhe {
  conciliacao_id: string
  transacao_id: string
  valor_aplicado: number
  titular_pix: string | null
  data_extrato: string
  descricao_tx: string | null
  origem_banco: string  // BRADESCO ou UNICRED
  conta_id: string | null
  natureza_lancamento: string | null
  aprovada_em: string | null
  origem: string | null
}

export async function getRealizadoPorLinha(
  orcamento_id: string
): Promise<RealizadoPorLinha[]> {
  const { data } = await apiClient.get<RealizadoPorLinha[]>(
    `/orcamentos/${orcamento_id}/realizado-por-linha`
  )
  return data
}

export async function getMargemPorContrato(
  competencia: string,
  empresa_id: string
): Promise<MargemPorContrato[]> {
  const { data } = await apiClient.get<MargemPorContrato[]>("/margem/por-contrato", {
    params: { competencia, empresa_id },
  })
  return data
}

export async function getMargemPorProfissional(
  contrato_id: string,
  competencia: string
): Promise<MargemPorProfissional[]> {
  const { data } = await apiClient.get<MargemPorProfissional[]>(
    "/margem/por-profissional",
    { params: { contrato_id, competencia } }
  )
  return data
}

export async function getConciliacoesDaLinha(
  linha_id: string
): Promise<ConciliacaoDetalhe[]> {
  const { data } = await apiClient.get<ConciliacaoDetalhe[]>(
    `/orcamentos/linhas/${linha_id}/conciliacoes`
  )
  return data
}
