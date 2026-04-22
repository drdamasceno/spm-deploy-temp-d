// frontend/lib/api/extratos.ts
import { apiClient } from "@/lib/api"
import type { UploadExtratoResponse } from "@/types/v2"

export async function uploadExtratoUnicred(
  conta_id: string,
  pdf: File | Blob
): Promise<UploadExtratoResponse> {
  const form = new FormData()
  form.append("conta_id", conta_id)
  form.append("arquivo", pdf)
  const { data } = await apiClient.post<UploadExtratoResponse>(
    "/extratos/unicred/upload",
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  )
  return data
}

export async function uploadExtratoBradesco(
  ofx: File | Blob
): Promise<UploadExtratoResponse> {
  const form = new FormData()
  form.append("arquivo", ofx)
  const { data } = await apiClient.post<UploadExtratoResponse>(
    "/extratos/bradesco/upload",
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  )
  return data
}
