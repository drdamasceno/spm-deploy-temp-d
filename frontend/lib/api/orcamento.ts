// frontend/lib/api/orcamento.ts
import { apiClient } from "@/lib/api"
import type {
  OrcamentoOut,
  OrcamentoLinhaOut,
  ResultadoUploadOrcamento,
} from "@/types/v2"

export interface ListarOrcamentosParams {
  empresa_id?: string
  competencia?: string
}

export async function listarOrcamentos(
  params: ListarOrcamentosParams = {}
): Promise<OrcamentoOut[]> {
  const { data } = await apiClient.get<OrcamentoOut[]>("/orcamentos", { params })
  return data
}

export interface CriarOrcamentoPayload {
  empresa_id: string
  competencia: string
}

export async function criarOrcamento(
  payload: CriarOrcamentoPayload
): Promise<OrcamentoOut> {
  const { data } = await apiClient.post<OrcamentoOut>("/orcamentos", payload)
  return data
}

export async function uploadOrcamento(
  empresa_id: string,
  competencia: string,
  arquivo: File | Blob
): Promise<ResultadoUploadOrcamento> {
  const form = new FormData()
  form.append("empresa_id", empresa_id)
  form.append("competencia", competencia)
  form.append("arquivo", arquivo)
  const { data } = await apiClient.post<ResultadoUploadOrcamento>(
    "/orcamentos/upload",
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  )
  return data
}

// Backend usa PATCH /orcamentos/{id}/validar (nao POST).
export async function validarOrcamento(id: string): Promise<OrcamentoOut> {
  const { data } = await apiClient.patch<OrcamentoOut>(`/orcamentos/${id}/validar`)
  return data
}

export async function replicarOrcamento(
  id: string,
  nova_competencia: string
): Promise<OrcamentoOut> {
  const { data } = await apiClient.post<OrcamentoOut>(
    `/orcamentos/${id}/replicar`,
    null,
    { params: { nova_competencia } }
  )
  return data
}

export async function deletarOrcamento(id: string): Promise<void> {
  await apiClient.delete(`/orcamentos/${id}`)
}

export async function listarLinhasDoOrcamento(
  orcamento_id: string,
  natureza?: string
): Promise<OrcamentoLinhaOut[]> {
  const params = natureza ? { natureza } : undefined
  const { data } = await apiClient.get<OrcamentoLinhaOut[]>(
    `/orcamentos/${orcamento_id}/linhas`,
    { params }
  )
  return data
}

export type OrcamentoLinhaPatch = Partial<{
  titular_razao_social: string
  titular_cpf_cnpj: string | null
  categoria_id: string | null
  projeto_id: string | null
  valor_previsto: number
  data_previsao: string | null
  observacao: string | null
}>

export async function editarOrcamentoLinha(
  linha_id: string,
  patch: OrcamentoLinhaPatch
): Promise<OrcamentoLinhaOut> {
  const { data } = await apiClient.patch<OrcamentoLinhaOut>(
    `/orcamentos/linhas/${linha_id}`,
    patch
  )
  return data
}

export async function deletarOrcamentoLinha(linha_id: string): Promise<void> {
  await apiClient.delete(`/orcamentos/linhas/${linha_id}`)
}
