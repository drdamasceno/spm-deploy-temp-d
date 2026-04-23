import { apiClient } from "@/lib/api"
import type { SplitRequest, SplitResponse } from "@/types/v2"

export async function fetchSplit(id: string): Promise<SplitResponse> {
  const { data } = await apiClient.get<SplitResponse>(`/transacoes/${id}/split`)
  return data
}

export async function fetchSplitSugerido(id: string): Promise<SplitResponse> {
  const { data } = await apiClient.get<SplitResponse>(`/transacoes/${id}/split/sugerir`)
  return data
}

export async function saveSplit(id: string, body: SplitRequest): Promise<SplitResponse> {
  const { data } = await apiClient.post<SplitResponse>(`/transacoes/${id}/split`, body)
  return data
}

export async function deleteSplit(id: string): Promise<void> {
  await apiClient.delete(`/transacoes/${id}/split`)
}
