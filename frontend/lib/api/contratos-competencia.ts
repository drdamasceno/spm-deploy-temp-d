// frontend/lib/api/contratos-competencia.ts
import { apiClient } from "@/lib/api"
import type {
  ContratoCidadeListItem,
  ContratoAnteriorItem,
  ContratoDetalheOut,
  ContratoDadosExtras,
} from "@/types/v2"

export async function listarContratos(
  params: { competencia?: string } = {}
): Promise<ContratoCidadeListItem[]> {
  const { data } = await apiClient.get<ContratoCidadeListItem[]>("/contratos", { params })
  return data
}

export async function listarContratosAnteriores(
  ate: string
): Promise<ContratoAnteriorItem[]> {
  const { data } = await apiClient.get<ContratoAnteriorItem[]>("/contratos/anteriores", {
    params: { ate },
  })
  return data
}

export async function listarContratosAnterioresFechadas(
  ate: string
): Promise<ContratoAnteriorItem[]> {
  const { data } = await apiClient.get<ContratoAnteriorItem[]>(
    "/contratos/anteriores-fechadas",
    { params: { ate } }
  )
  return data
}

export async function fetchContratoCompetencia(
  contrato_id: string,
  competencia: string
): Promise<ContratoDetalheOut> {
  const { data } = await apiClient.get<ContratoDetalheOut>(
    `/contratos/${contrato_id}/competencia/${competencia}`
  )
  return data
}

export async function editarDadosContrato(
  contrato_id: string,
  patch: ContratoDadosExtras
): Promise<ContratoDadosExtras> {
  const { data } = await apiClient.patch<ContratoDadosExtras>(
    `/contratos/${contrato_id}`,
    patch
  )
  return data
}
