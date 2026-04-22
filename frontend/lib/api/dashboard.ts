// frontend/lib/api/dashboard.ts
import { apiClient } from "@/lib/api"
import type { DashboardResponse, EmpresaCodigo } from "@/types/v2"

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
