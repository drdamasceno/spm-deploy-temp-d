import { apiClient } from "@/lib/api"

export interface TxIntragrupoPendente {
  id: string
  valor: number
  titular_pix: string | null
  data_extrato: string
  descricao: string | null
  status_conciliacao: string
  categoria: string
}

export interface ConciliacaoLoteResult {
  transacao_id: string
  empresa_destino_id: string
  valor_total_tx: number
  valor_consumido: number
  residuo_nao_consumido: number
  conciliadas: Array<{
    orcamento_linha_id: string
    titular_razao_social: string | null
    valor_aplicado: number
  }>
  linhas_remanescentes_em_aberto: number
}

export async function fetchIntragrupoPendentes(): Promise<TxIntragrupoPendente[]> {
  const { data } = await apiClient.get<{ transacoes: TxIntragrupoPendente[] }>(
    "/conciliacoes/intragrupo/pendentes"
  )
  return data.transacoes
}

export async function conciliarIntragrupoLote(
  transacaoId: string
): Promise<ConciliacaoLoteResult> {
  const { data } = await apiClient.post<ConciliacaoLoteResult>(
    `/conciliacoes/intragrupo/${transacaoId}`
  )
  return data
}
