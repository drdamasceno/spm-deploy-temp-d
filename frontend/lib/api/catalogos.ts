// frontend/lib/api/catalogos.ts
import { apiClient } from "@/lib/api"
import type { EmpresaOut, CategoriaOut, ProjetoOut } from "@/types/v2"

export async function listarEmpresas(): Promise<EmpresaOut[]> {
  const { data } = await apiClient.get<EmpresaOut[]>("/empresas")
  return data
}

export async function listarCategorias(): Promise<CategoriaOut[]> {
  const { data } = await apiClient.get<CategoriaOut[]>("/categorias")
  return data
}

export async function listarProjetos(): Promise<ProjetoOut[]> {
  const { data } = await apiClient.get<ProjetoOut[]>("/projetos")
  return data
}

export interface CriarProjetoPayload {
  codigo: string
  descricao?: string | null
  empresa_id: string
}

export async function criarProjeto(payload: CriarProjetoPayload): Promise<ProjetoOut> {
  const { data } = await apiClient.post<ProjetoOut>("/projetos", payload)
  return data
}

export async function deletarProjeto(id: string): Promise<void> {
  await apiClient.delete(`/projetos/${id}`)
}

export interface ContaBancariaOut {
  id: string
  banco: string
  agencia: string
  conta: string
  finalidade: string
  ativo: boolean
}

export async function listarContasBancarias(
  params: { finalidade?: string } = {}
): Promise<ContaBancariaOut[]> {
  const { data } = await apiClient.get<ContaBancariaOut[]>("/contas_bancarias", { params })
  return data
}

export type FinalidadeConta =
  | "RECEBIMENTOS"
  | "REMESSAS"
  | "AVISTA"
  | "FIXAS"
  | "TRIBUTOS"

export interface ContaBancariaCreate {
  banco: string
  agencia: string
  conta: string
  finalidade: FinalidadeConta
}

export async function criarContaBancaria(
  payload: ContaBancariaCreate
): Promise<ContaBancariaOut> {
  const { data } = await apiClient.post<ContaBancariaOut>("/contas_bancarias", payload)
  return data
}

export async function desativarContaBancaria(id: string): Promise<void> {
  await apiClient.delete(`/contas_bancarias/${id}`)
}
