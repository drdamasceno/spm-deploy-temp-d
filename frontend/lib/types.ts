export type UserInfo = {
  id: string
  email: string
}

export type LoginResponse = {
  access_token: string
  refresh_token: string
  user: UserInfo
}

export type MeResponse = {
  id: string
  email: string
  nome: string | null
  role: string | null
}

export type ExtratoPeriodo = {
  inicio: string
  fim: string
}

export type UploadRodadaResponse = {
  rodada_id: string
  pp_competencias: string[]
  extrato_periodo: ExtratoPeriodo
  total_registros_pp: number
  total_transacoes: number
}

export type ResumoTransacoes = {
  match_automatico: number
  fracionado: number
  conciliado_categoria: number
  manual_pendente: number
  nao_classificado: number
}

export type ResumoRegistrosPP = {
  total_elegivel: number
  sem_movimento: number
  saldo_negativo: number
}

export type ConciliarResponse = {
  rodada_id: string
  resumo_transacoes: ResumoTransacoes
  resumo_registros_pp: ResumoRegistrosPP
  valor_total_pp: number
  valor_total_conciliado: number
  percentual_conciliado: number
}

export type RegistroPPNested = {
  id: string
  prestador_nome: string | null
  contrato_nome: string | null
  mes_competencia: string
  saldo_pp: number
  status_saldo: string
}

export type TransacaoResultado = {
  id: string
  valor: number
  data_extrato: string
  titular_pix: string | null
  descricao: string | null
  status_conciliacao: string
  categoria: string | null
  registro_pp_id: string | null
  registro_pp: RegistroPPNested | null
}

export type Pagination = {
  page: number
  per_page: number
  total: number
}

export type ResultadoResponse = ConciliarResponse & {
  transacoes: TransacaoResultado[]
  pagination: Pagination
}

export type RodadaListItem = {
  id: string
  periodo_extrato_inicio: string
  periodo_extrato_fim: string
  pp_competencias: string[]
  status: string
  criado_em: string
  criado_por: string | null
}

export type StatusConciliacao =
  | "MATCH_AUTOMATICO"
  | "FRACIONADO"
  | "CONCILIADO_POR_CATEGORIA"
  | "MANUAL_PENDENTE"
  | "NAO_CLASSIFICADO"

export const STATUS_LABELS: Record<StatusConciliacao, string> = {
  MATCH_AUTOMATICO: "Match automatico",
  FRACIONADO: "Fracionado",
  CONCILIADO_POR_CATEGORIA: "Conciliado por categoria",
  MANUAL_PENDENTE: "Manual pendente",
  NAO_CLASSIFICADO: "Nao classificado",
}

export const STATUS_VARIANTS: Record<StatusConciliacao, "default" | "secondary" | "destructive" | "outline"> = {
  MATCH_AUTOMATICO: "default",
  FRACIONADO: "default",
  CONCILIADO_POR_CATEGORIA: "secondary",
  MANUAL_PENDENTE: "outline",
  NAO_CLASSIFICADO: "destructive",
}
