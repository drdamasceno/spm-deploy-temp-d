// frontend/lib/api/adiantamento.ts
import { apiClient } from "@/lib/api"
import type { AdiantamentoOut } from "@/types/v2"

export interface ListarAdiantamentosParams {
  status_filtro?: AdiantamentoOut["status"]
  prestador_id?: string
}

export async function listarAdiantamentos(
  params: ListarAdiantamentosParams = {}
): Promise<AdiantamentoOut[]> {
  const { data } = await apiClient.get<AdiantamentoOut[]>("/adiantamentos", {
    params,
  })
  return data
}

export async function compensarAdiantamento(
  id: string,
  registro_pp_id: string
): Promise<AdiantamentoOut> {
  const { data } = await apiClient.post<AdiantamentoOut>(
    `/adiantamentos/${id}/compensar`,
    { registro_pp_id }
  )
  return data
}

export interface RegistroPPDisponivel {
  id: string;
  contrato_id: string;
  mes_competencia: string;
  saldo_pp: number;
  status_saldo: string;
  contrato: { nome: string } | null;
}

export async function listarRegistrosDisponiveis(
  adiantamento_id: string
): Promise<RegistroPPDisponivel[]> {
  const { data } = await apiClient.get<RegistroPPDisponivel[]>(
    `/adiantamentos/${adiantamento_id}/registros_pp_disponiveis`
  )
  return data
}
