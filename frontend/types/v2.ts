// frontend/types/v2.ts
export type EmpresaCodigo = "SPM" | "FD" | "TODAS";

export interface EmpresaOut {
  id: string;
  codigo: string;
  razao_social: string;
  cnpj: string | null;
  ativa: boolean;
}

export interface CategoriaOut {
  id: string;
  nome: string;
  descricao: string | null;
}

export interface ProjetoOut {
  id: string;
  codigo: string;
  descricao: string | null;
  empresa_id: string;
  ativo: boolean;
}

export type NaturezaOrcamento =
  | "DESPESA_FIXA"
  | "TRIBUTO"
  | "SALARIO_VARIAVEL"
  | "COMISSAO"
  | "VALOR_VARIAVEL"
  | "DESPESA_PROFISSIONAIS";

export interface OrcamentoOut {
  id: string;
  empresa_id: string;
  competencia: string;
  status: "RASCUNHO" | "VALIDADO" | "FECHADO";
  criado_em: string;
}

export interface OrcamentoLinhaOut {
  id: string;
  orcamento_id: string;
  natureza: NaturezaOrcamento;
  categoria_id: string | null;
  projeto_id: string | null;
  titular_cpf_cnpj: string | null;
  titular_razao_social: string;
  contrato_id: string | null;
  valor_previsto: number;
  data_previsao: string | null;
  observacao: string | null;
}

export interface ResultadoUploadOrcamento {
  orcamento_id: string;
  total_linhas_inseridas: number;
  linhas_por_secao: Record<NaturezaOrcamento, number>;
  linhas_descartadas: number;
  avisos: string[];
}

export interface UploadExtratoResponse {
  conta_id: string;
  origem_banco: "UNICRED" | "BRADESCO";
  total_transacoes_inseridas: number;
  periodo_inicio: string;
  periodo_fim: string;
  saldo_final: number;
}

export type OrigemSugestao = "REGRA" | "SIMILARIDADE" | "VALOR" | "MANUAL";

export interface SugestaoOut {
  transacao_id: string;
  orcamento_linha_id: string;
  confianca: number;
  origem: OrigemSugestao;
  valor_aplicado: number;
}

export interface ConciliacaoCreate {
  transacao_id: string;
  orcamento_linha_id: string;
  valor_aplicado: number;
  confianca: number | null;
  origem: OrigemSugestao;
}

export interface ConciliacaoOut extends ConciliacaoCreate {
  id: string;
  aprovada_em: string;
}

export interface RegraClassificacaoOut {
  id: string;
  titular_pix_padrao: string;
  orcamento_linha_id: string | null;
  categoria_id: string | null;
  projeto_id: string | null;
  empresa_id: string | null;
  confianca_base: number;
  uso_count: number;
  ativa: boolean;
  ultima_utilizacao: string | null;
}

export interface AdiantamentoOut {
  id: string;
  prestador_id: string;
  valor_bruto_solicitado: number;
  percentual_desconto: number;
  valor_liquido_pago: number;
  receita_financeira: number;
  data_pagamento: string;
  status: "ABERTO" | "COMPENSADO_PARCIAL" | "COMPENSADO_TOTAL" | "BAIXADO_MANUAL";
  compensado_em_registro_pp_id: string | null;
}

export interface PrestadorLinha {
  nome: string;
  valor_pp: number;
  valor_pago: number;
  datas_pix: string[];
  status: "PAGO" | "PARCIAL" | "PENDENTE" | "SEM_MOVIMENTO";
}

export interface ContratoCompetenciaOut {
  contrato_id: string;
  nome_contrato: string;
  competencia: string;
  total_devido: number;
  total_pago: number;
  percentual_pago: number;
  receita_prevista: number | null;
  margem_projetada: number | null;
  prestadores: PrestadorLinha[];
}

export interface KPIs {
  saldo_inicial: number;
  saidas_mes: number;
  previsto_a_pagar: number;
  saldo_atual: number;
}

export interface BarraPxR {
  categoria: string;
  previsto: number;
  realizado: number;
  pct: number;
}

export interface Alerta {
  tipo: "NAO_CONCILIADO" | "VENCIDO" | "PAGO_A_MAIOR" | "ESTORNO";
  mensagem: string;
  ref_id: string | null;
  ref_tipo: string | null;
}

export interface DashboardResponse {
  competencia: string;
  empresa_filtro: string;
  kpis: KPIs;
  saidas_por_natureza: Record<string, number>;
  previsto_x_realizado: BarraPxR[];
  alertas: Alerta[];
}

// Contratos por cidade (Track C)
export interface ContratoCidadeListItem {
  id: string
  uf: string
  cidade: string
  competencia: string
  total: number
  total_pago: number
  saldo: number
  prestadores: number
  status: "PAGO" | "PARCIAL" | "PENDENTE"
}

export interface ContratoAnteriorItem {
  contrato_id: string
  uf: string
  cidade: string
  competencia: string
  total_original: number
  total_pago: number
  saldo_aberto: number
  prestadores: number
  status: "PAGO" | "PARCIAL" | "PENDENTE"
  idade_dias: number
}

export interface PrestadorLinhaDetalhe {
  prestador_id: string
  prestador_nome: string
  local: string | null
  competencia: string
  total: number
  total_pago: number
  saldo: number
  status: "PAGO" | "PARCIAL" | "PENDENTE"
  data_pagamento: string | null
}

export interface ContratoDadosExtras {
  nome_oficial?: string | null
  cnpj?: string | null
  tipo?: "PUBLICO" | "PRIVADO" | null
  valor_faturamento_mensal?: number | null
  retencao_tributaria_pct?: number | null
  observacoes?: string | null
}

export interface ContratoDetalheOut {
  contrato_id: string
  uf: string
  cidade: string
  competencia: string
  total: number
  total_pago: number
  saldo: number
  prestadores_count: number
  registros_count: number
  linhas: PrestadorLinhaDetalhe[]
  dados_extras: ContratoDadosExtras
}

// Saldos Dashboard (Track D)
export type TipoAplicacao = "CDB" | "LCA" | "LCI" | "FUNDO" | "POUPANCA" | "TESOURO" | "ACOES" | "FII" | "OUTROS"
export type ModoAplicacao = "AUTOMATICA" | "MANUAL"
export type LiquidezAplicacao = "DIARIA" | "VENCIMENTO" | "D30" | "D90" | "D180"

export interface ContaLiquidezItem {
  conta_id: string
  banco: string
  agencia: string
  conta: string
  finalidade: string
  saldo_valor: number
  data_referencia: string | null
  origem: "BRADESCO_OFX" | "UNICRED_PDF" | "MANUAL" | null
  dias_desatualizado: number | null
}

export interface AplicacaoOut {
  id: string
  nome: string
  tipo: TipoAplicacao
  valor_atual: number
  data_atualizacao: string
  modo: ModoAplicacao
  instituicao?: string | null
  rentabilidade?: string | null
  data_vencimento?: string | null
  liquidez?: LiquidezAplicacao | null
  observacoes?: string | null
  ativo: boolean
}

export interface AplicacaoCreate {
  nome: string
  tipo: TipoAplicacao
  valor_atual: number
  data_atualizacao?: string
  modo: ModoAplicacao
  instituicao?: string | null
  rentabilidade?: string | null
  data_vencimento?: string | null
  liquidez?: LiquidezAplicacao | null
  observacoes?: string | null
}

export type AplicacaoPatch = Partial<AplicacaoCreate> & { ativo?: boolean }

export interface DashboardSaldos {
  contas: ContaLiquidezItem[]
  aplicacoes: AplicacaoOut[]
  liquidez_total: number
  disponivel_agora: number
  reserva_travada: number
}

export interface SaldoManualInput {
  conta_bancaria_id: string
  saldo_valor: number
  data_referencia: string
  observacao?: string | null
}
