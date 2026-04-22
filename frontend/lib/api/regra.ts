// frontend/lib/api/regra.ts
import { apiClient } from "@/lib/api"
import type { RegraClassificacaoOut } from "@/types/v2"

export interface ListarRegrasParams {
  ativa?: boolean
}

export async function listarRegras(
  params: ListarRegrasParams = {}
): Promise<RegraClassificacaoOut[]> {
  const { data } = await apiClient.get<RegraClassificacaoOut[]>("/regras", { params })
  return data
}

export interface RegraPatch {
  ativa?: boolean
  confianca_base?: number
}

export async function editarRegra(
  id: string,
  patch: RegraPatch
): Promise<RegraClassificacaoOut> {
  const { data } = await apiClient.patch<RegraClassificacaoOut>(`/regras/${id}`, patch)
  return data
}

export async function desativarRegra(id: string): Promise<void> {
  await apiClient.delete(`/regras/${id}`)
}
