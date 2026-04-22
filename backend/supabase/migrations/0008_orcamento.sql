-- 0008_orcamento.sql
-- Orçamento mensal: cabeçalho + linhas + enum de natureza + view de status

-- ============================================================
-- Enums
-- ============================================================
CREATE TYPE natureza_orcamento AS ENUM (
  'DESPESA_FIXA',
  'TRIBUTO',
  'SALARIO_VARIAVEL',
  'COMISSAO',
  'VALOR_VARIAVEL',
  'DESPESA_PROFISSIONAIS'
);

-- ============================================================
-- Tabela: orcamento (cabeçalho)
-- ============================================================
CREATE TABLE orcamento (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id uuid NOT NULL REFERENCES empresa(id),
  competencia text NOT NULL CHECK (competencia ~ '^\d{4}-\d{2}$'),
  status text NOT NULL DEFAULT 'RASCUNHO'
    CHECK (status IN ('RASCUNHO', 'VALIDADO', 'FECHADO')),
  criado_por uuid REFERENCES usuario(id),
  criado_em timestamptz NOT NULL DEFAULT now(),
  validado_em timestamptz,
  fechado_em timestamptz,
  UNIQUE (empresa_id, competencia)
);
CREATE INDEX idx_orcamento_competencia ON orcamento(competencia);
CREATE INDEX idx_orcamento_empresa ON orcamento(empresa_id);

-- ============================================================
-- Tabela: orcamento_linha
-- ============================================================
CREATE TABLE orcamento_linha (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  orcamento_id uuid NOT NULL REFERENCES orcamento(id) ON DELETE CASCADE,
  natureza natureza_orcamento NOT NULL,
  categoria_id uuid REFERENCES categoria_despesa(id),
  projeto_id uuid REFERENCES projeto(id),
  titular_cpf_cnpj text,
  titular_razao_social text NOT NULL,
  contrato_id uuid REFERENCES contrato(id),
  valor_previsto numeric(14,2) NOT NULL CHECK (valor_previsto >= 0),
  data_previsao date,
  observacao text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_linha_orcamento ON orcamento_linha(orcamento_id);
CREATE INDEX idx_linha_natureza ON orcamento_linha(natureza);
CREATE INDEX idx_linha_titular ON orcamento_linha(lower(titular_razao_social));
CREATE INDEX idx_linha_contrato ON orcamento_linha(contrato_id) WHERE contrato_id IS NOT NULL;

-- ============================================================
-- RLS
-- ============================================================
ALTER TABLE orcamento ENABLE ROW LEVEL SECURITY;
ALTER TABLE orcamento_linha ENABLE ROW LEVEL SECURITY;

CREATE POLICY orcamento_select ON orcamento FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY orcamento_insert ON orcamento FOR INSERT WITH CHECK (auth.uid() IS NOT NULL AND criado_por = auth.uid());
CREATE POLICY orcamento_update ON orcamento FOR UPDATE
  USING (fn_is_ceo() OR (criado_por = auth.uid() AND status <> 'FECHADO'));
CREATE POLICY orcamento_delete ON orcamento FOR DELETE USING (fn_is_ceo());

CREATE POLICY linha_select ON orcamento_linha FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY linha_insert ON orcamento_linha FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY linha_update ON orcamento_linha FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY linha_delete ON orcamento_linha FOR DELETE USING (auth.uid() IS NOT NULL);

-- ============================================================
-- Triggers de log_auditoria
-- ============================================================
CREATE TRIGGER trg_audit_orcamento AFTER INSERT OR UPDATE OR DELETE ON orcamento
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();
CREATE TRIGGER trg_audit_orcamento_linha AFTER INSERT OR UPDATE OR DELETE ON orcamento_linha
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

-- ============================================================
-- Grants
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON orcamento, orcamento_linha TO authenticated;
