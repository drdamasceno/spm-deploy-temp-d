-- 0001_schema_inicial.sql
-- Schema v1 SPM Sistema Financeiro
-- Escopo: 6 entidades ativas + ADIANTAMENTO parcial + EXCECAO_PJ + REGISTRO_PP
-- REGISTRO_PP incluida por bloco [ANCORADA] "Registros PP com saldo <= 0"
-- Motor 19fa14b NAO refatorado aqui — schema representa as regras que levaram aos 93,5%

-- =====================================================
-- 1. EXTENSIONS
-- =====================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- 2. ENUMS
-- =====================================================
CREATE TYPE perfil_usuario AS ENUM (
  'CEO', 'VALIDADOR', 'OPERADOR_FINANCEIRO', 'CONCILIADOR', 'OPERADOR_ESCALAS'
);

CREATE TYPE finalidade_conta AS ENUM (
  'RECEBIMENTOS', 'REMESSAS', 'AVISTA', 'FIXAS', 'TRIBUTOS'
);

CREATE TYPE tipo_conta AS ENUM ('CORRENTE', 'POUPANCA');

CREATE TYPE tipo_contrato AS ENUM ('PUBLICO', 'PRIVADO');

CREATE TYPE status_contrato AS ENUM ('ATIVO', 'ENCERRADO', 'SUSPENSO');

CREATE TYPE tipo_transacao AS ENUM ('CREDITO', 'DEBITO');

-- Regra ancorada 21: 5 status de conciliacao
CREATE TYPE status_conciliacao AS ENUM (
  'MATCH_AUTOMATICO',
  'FRACIONADO',
  'CONCILIADO_POR_CATEGORIA',
  'MANUAL_PENDENTE',
  'NAO_CLASSIFICADO'
);

-- Regra ancorada 18: 7 categorias de conciliacao
CREATE TYPE categoria_conciliacao AS ENUM (
  'ADIANTAMENTO_AVISTA',
  'COMPETENCIA_ANTERIOR',
  'CLT_FOLHA',
  'DESPESA_OPERACIONAL',
  'COORDENADORA_CLT_PJ',
  'EXCECAO_PJ_PRESTADOR',
  'TRANSFERENCIA_INTERNA'
);

-- Regra ancorada "Registros PP com saldo <= 0"
CREATE TYPE status_saldo_pp AS ENUM (
  'ELEGIVEL', 'SEM_MOVIMENTO', 'SALDO_NEGATIVO'
);

CREATE TYPE acao_auditoria AS ENUM ('INSERT', 'UPDATE', 'DELETE');

-- =====================================================
-- 3. TABELAS
-- =====================================================

-- USUARIO (1:1 com auth.users do Supabase)
CREATE TABLE usuario (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  nome text NOT NULL,
  email text NOT NULL UNIQUE,
  perfil perfil_usuario NOT NULL,
  fa_habilitado boolean NOT NULL DEFAULT false,
  totp_secret text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- PRESTADOR
-- Regra ancorada 20: tipo_doc decide a chave de match (CPF -> nome; CNPJ -> razao_social_pj + EXCECAO_PJ)
CREATE TABLE prestador (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome text NOT NULL,
  registro_profissional text,
  uf text,
  ficticio boolean NOT NULL DEFAULT false,
  tipo_doc text NOT NULL CHECK (tipo_doc IN ('CPF', 'CNPJ')),
  cpf_cnpj text NOT NULL,
  razao_social_pj text,
  banco text,
  agencia text,
  conta text,
  tipo_conta tipo_conta,
  titular_pix text,
  chave_pix text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_prestador_nome ON prestador (lower(nome));
CREATE INDEX idx_prestador_razao_social_pj ON prestador (lower(razao_social_pj));
CREATE INDEX idx_prestador_cpf_cnpj ON prestador (cpf_cnpj);

-- CONTRATO
-- Regra ancorada 16: local_pp e a chave de match contra coluna "Local" do XLSX do PP
CREATE TABLE contrato (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome text NOT NULL,
  contratante text,
  cnpj text,
  tipo tipo_contrato NOT NULL,
  status status_contrato NOT NULL DEFAULT 'ATIVO',
  local_pp text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_contrato_local_pp ON contrato (lower(local_pp));

-- CONTA_BANCARIA
CREATE TABLE conta_bancaria (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  banco text NOT NULL,
  agencia text NOT NULL,
  conta text NOT NULL,
  finalidade finalidade_conta NOT NULL,
  ativo boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (banco, agencia, conta)
);

-- REGISTRO_PP
-- Regra ancorada "Registros PP com saldo <= 0"
-- Fonte: motor conciliacao_spm.py linhas 212-225
CREATE TABLE registro_pp (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prestador_id uuid NOT NULL REFERENCES prestador(id) ON DELETE RESTRICT,
  contrato_id uuid NOT NULL REFERENCES contrato(id) ON DELETE RESTRICT,
  mes_competencia text NOT NULL CHECK (mes_competencia ~ '^\d{4}-\d{2}$'),
  saldo_pp numeric(14,2) NOT NULL,
  status_saldo status_saldo_pp NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (prestador_id, contrato_id, mes_competencia)
);
CREATE INDEX idx_registro_pp_competencia ON registro_pp (mes_competencia);
CREATE INDEX idx_registro_pp_status ON registro_pp (status_saldo);

-- TRANSACAO_BANCARIA
-- Regra ancorada 18: categoria obrigatoria apenas em CONCILIADO_POR_CATEGORIA
CREATE TABLE transacao_bancaria (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conta_id uuid NOT NULL REFERENCES conta_bancaria(id) ON DELETE RESTRICT,
  valor numeric(14,2) NOT NULL,
  data_extrato date NOT NULL,
  mes_competencia text NOT NULL CHECK (mes_competencia ~ '^\d{4}-\d{2}$'),
  tipo tipo_transacao NOT NULL,
  status_conciliacao status_conciliacao NOT NULL,
  categoria categoria_conciliacao,
  descricao text,
  titular_pix text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_categoria_somente_se_conciliado_por_categoria CHECK (
    (status_conciliacao = 'CONCILIADO_POR_CATEGORIA' AND categoria IS NOT NULL)
    OR (status_conciliacao <> 'CONCILIADO_POR_CATEGORIA' AND categoria IS NULL)
  )
);
CREATE INDEX idx_tx_conta_data ON transacao_bancaria (conta_id, data_extrato);
CREATE INDEX idx_tx_competencia ON transacao_bancaria (mes_competencia);
CREATE INDEX idx_tx_status ON transacao_bancaria (status_conciliacao);
CREATE INDEX idx_tx_categoria ON transacao_bancaria (categoria);

-- ADIANTAMENTO (parcial — cadastro manual; pipeline automatizado fica pra Fase 2)
CREATE TABLE adiantamento (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prestador_id uuid NOT NULL REFERENCES prestador(id) ON DELETE RESTRICT,
  valor_bruto_solicitado numeric(14,2) NOT NULL CHECK (valor_bruto_solicitado > 0),
  percentual_desconto numeric(5,2) NOT NULL CHECK (percentual_desconto BETWEEN 3 AND 8),
  valor_liquido_pago numeric(14,2) NOT NULL CHECK (valor_liquido_pago > 0),
  receita_financeira numeric(14,2) GENERATED ALWAYS AS (valor_bruto_solicitado - valor_liquido_pago) STORED,
  autorizado_por uuid NOT NULL REFERENCES usuario(id),
  data_pagamento date NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_adiantamento_prestador ON adiantamento (prestador_id);

-- EXCECAO_PJ
CREATE TABLE excecao_pj (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prestador_id uuid NOT NULL REFERENCES prestador(id) ON DELETE CASCADE,
  razao_social_autorizada text NOT NULL,
  cnpj text,
  data_aprovacao date NOT NULL,
  justificativa text,
  aprovado_por uuid NOT NULL REFERENCES usuario(id),
  ativo boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_excecao_pj_prestador ON excecao_pj (prestador_id);
CREATE INDEX idx_excecao_pj_razao ON excecao_pj (lower(razao_social_autorizada));

-- LOG_AUDITORIA (append-only)
CREATE TABLE log_auditoria (
  id bigserial PRIMARY KEY,
  tabela text NOT NULL,
  registro_id uuid NOT NULL,
  acao acao_auditoria NOT NULL,
  usuario_id uuid REFERENCES usuario(id),
  timestamp timestamptz NOT NULL DEFAULT now(),
  dados_anteriores jsonb,
  dados_novos jsonb
);
CREATE INDEX idx_log_tabela_registro ON log_auditoria (tabela, registro_id);
CREATE INDEX idx_log_timestamp ON log_auditoria (timestamp DESC);
CREATE INDEX idx_log_usuario ON log_auditoria (usuario_id);

-- =====================================================
-- 4. TRIGGER LOG_AUDITORIA (automatico em todas tabelas)
-- =====================================================
CREATE OR REPLACE FUNCTION fn_log_auditoria()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_usuario_id uuid;
  v_registro_id uuid;
BEGIN
  BEGIN
    v_usuario_id := auth.uid();
  EXCEPTION WHEN OTHERS THEN
    v_usuario_id := NULL;
  END;

  IF TG_OP = 'DELETE' THEN
    v_registro_id := OLD.id;
    INSERT INTO log_auditoria (tabela, registro_id, acao, usuario_id, dados_anteriores, dados_novos)
    VALUES (TG_TABLE_NAME, v_registro_id, 'DELETE', v_usuario_id, to_jsonb(OLD), NULL);
    RETURN OLD;
  ELSIF TG_OP = 'UPDATE' THEN
    v_registro_id := NEW.id;
    INSERT INTO log_auditoria (tabela, registro_id, acao, usuario_id, dados_anteriores, dados_novos)
    VALUES (TG_TABLE_NAME, v_registro_id, 'UPDATE', v_usuario_id, to_jsonb(OLD), to_jsonb(NEW));
    RETURN NEW;
  ELSIF TG_OP = 'INSERT' THEN
    v_registro_id := NEW.id;
    INSERT INTO log_auditoria (tabela, registro_id, acao, usuario_id, dados_anteriores, dados_novos)
    VALUES (TG_TABLE_NAME, v_registro_id, 'INSERT', v_usuario_id, NULL, to_jsonb(NEW));
    RETURN NEW;
  END IF;
  RETURN NULL;
END;
$$;

CREATE TRIGGER trg_audit_usuario
  AFTER INSERT OR UPDATE OR DELETE ON usuario
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

CREATE TRIGGER trg_audit_prestador
  AFTER INSERT OR UPDATE OR DELETE ON prestador
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

CREATE TRIGGER trg_audit_contrato
  AFTER INSERT OR UPDATE OR DELETE ON contrato
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

CREATE TRIGGER trg_audit_conta_bancaria
  AFTER INSERT OR UPDATE OR DELETE ON conta_bancaria
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

CREATE TRIGGER trg_audit_registro_pp
  AFTER INSERT OR UPDATE OR DELETE ON registro_pp
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

CREATE TRIGGER trg_audit_transacao_bancaria
  AFTER INSERT OR UPDATE OR DELETE ON transacao_bancaria
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

CREATE TRIGGER trg_audit_adiantamento
  AFTER INSERT OR UPDATE OR DELETE ON adiantamento
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

CREATE TRIGGER trg_audit_excecao_pj
  AFTER INSERT OR UPDATE OR DELETE ON excecao_pj
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

-- =====================================================
-- 5. updated_at automatico
-- =====================================================
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_updated_at_usuario
  BEFORE UPDATE ON usuario FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_updated_at_prestador
  BEFORE UPDATE ON prestador FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_updated_at_contrato
  BEFORE UPDATE ON contrato FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- =====================================================
-- 6. RLS — Helper + Policies basicas (v1)
-- =====================================================

CREATE OR REPLACE FUNCTION fn_is_ceo()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.usuario
    WHERE id = auth.uid() AND perfil = 'CEO'
  );
$$;

ALTER TABLE usuario             ENABLE ROW LEVEL SECURITY;
ALTER TABLE prestador           ENABLE ROW LEVEL SECURITY;
ALTER TABLE contrato            ENABLE ROW LEVEL SECURITY;
ALTER TABLE conta_bancaria      ENABLE ROW LEVEL SECURITY;
ALTER TABLE registro_pp         ENABLE ROW LEVEL SECURITY;
ALTER TABLE transacao_bancaria  ENABLE ROW LEVEL SECURITY;
ALTER TABLE adiantamento        ENABLE ROW LEVEL SECURITY;
ALTER TABLE excecao_pj          ENABLE ROW LEVEL SECURITY;
ALTER TABLE log_auditoria       ENABLE ROW LEVEL SECURITY;

-- USUARIO: ve apenas proprio row; CEO ve todos
CREATE POLICY usuario_select_self_or_ceo ON usuario
  FOR SELECT USING (id = auth.uid() OR fn_is_ceo());
CREATE POLICY usuario_update_self_or_ceo ON usuario
  FOR UPDATE USING (id = auth.uid() OR fn_is_ceo());
CREATE POLICY usuario_insert_ceo ON usuario
  FOR INSERT WITH CHECK (fn_is_ceo());
CREATE POLICY usuario_delete_ceo ON usuario
  FOR DELETE USING (fn_is_ceo());

-- Demais tabelas operacionais: authenticated faz SELECT/INSERT/UPDATE; so CEO deleta
CREATE POLICY prestador_select ON prestador
  FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY prestador_insert ON prestador
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY prestador_update ON prestador
  FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY prestador_delete ON prestador
  FOR DELETE USING (fn_is_ceo());

CREATE POLICY contrato_select ON contrato
  FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY contrato_insert ON contrato
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY contrato_update ON contrato
  FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY contrato_delete ON contrato
  FOR DELETE USING (fn_is_ceo());

CREATE POLICY conta_bancaria_select ON conta_bancaria
  FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY conta_bancaria_insert ON conta_bancaria
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY conta_bancaria_update ON conta_bancaria
  FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY conta_bancaria_delete ON conta_bancaria
  FOR DELETE USING (fn_is_ceo());

CREATE POLICY registro_pp_select ON registro_pp
  FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY registro_pp_insert ON registro_pp
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY registro_pp_update ON registro_pp
  FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY registro_pp_delete ON registro_pp
  FOR DELETE USING (fn_is_ceo());

CREATE POLICY transacao_bancaria_select ON transacao_bancaria
  FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY transacao_bancaria_insert ON transacao_bancaria
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY transacao_bancaria_update ON transacao_bancaria
  FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY transacao_bancaria_delete ON transacao_bancaria
  FOR DELETE USING (fn_is_ceo());

CREATE POLICY adiantamento_select ON adiantamento
  FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY adiantamento_insert ON adiantamento
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY adiantamento_update ON adiantamento
  FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY adiantamento_delete ON adiantamento
  FOR DELETE USING (fn_is_ceo());

CREATE POLICY excecao_pj_select ON excecao_pj
  FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY excecao_pj_insert ON excecao_pj
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY excecao_pj_update ON excecao_pj
  FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY excecao_pj_delete ON excecao_pj
  FOR DELETE USING (fn_is_ceo());

-- LOG_AUDITORIA: append-only
CREATE POLICY log_select_own_or_ceo ON log_auditoria
  FOR SELECT USING (usuario_id = auth.uid() OR fn_is_ceo());
-- Sem policies UPDATE/DELETE => bloqueio total. INSERT via trigger SECURITY DEFINER.

REVOKE UPDATE, DELETE ON log_auditoria FROM authenticated;
REVOKE UPDATE, DELETE ON log_auditoria FROM anon;

-- =====================================================
-- 7. GRANTS
-- =====================================================
GRANT USAGE ON SCHEMA public TO authenticated, anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON
  usuario, prestador, contrato, conta_bancaria,
  registro_pp, transacao_bancaria, adiantamento, excecao_pj
TO authenticated;
GRANT SELECT, INSERT ON log_auditoria TO authenticated;
GRANT USAGE ON SEQUENCE log_auditoria_id_seq TO authenticated;
