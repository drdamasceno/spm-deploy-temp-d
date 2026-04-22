-- 0009_conciliacao_regra_extensoes.sql
-- Tabela associativa extrato↔orçamento + regras aprendíveis + extensões
-- em tabelas existentes (transacao_bancaria, registro_pp, adiantamento)

-- ============================================================
-- Enums novos
-- ============================================================
CREATE TYPE adiantamento_status AS ENUM (
  'ABERTO',
  'COMPENSADO_PARCIAL',
  'COMPENSADO_TOTAL',
  'BAIXADO_MANUAL'
);

CREATE TYPE origem_banco AS ENUM ('BRADESCO', 'UNICRED');

CREATE TYPE natureza_lancamento AS ENUM (
  'PIX_CREDITO',
  'PIX_DEBITO',
  'PIX_TEF',
  'LIQUIDACAO_TITULO',
  'CONVENIO',
  'INTEGRALIZACAO_CAPITAL',
  'ARRECADACAO',
  'TARIFA_CONTA',
  'ESTORNO',
  'OUTRO'
);

CREATE TYPE origem_conciliacao AS ENUM ('REGRA', 'SIMILARIDADE', 'VALOR', 'MANUAL');

-- ============================================================
-- Tabela: conciliacao_orcamento (associativa N:N)
-- ============================================================
CREATE TABLE conciliacao_orcamento (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  transacao_id uuid NOT NULL REFERENCES transacao_bancaria(id) ON DELETE CASCADE,
  orcamento_linha_id uuid NOT NULL REFERENCES orcamento_linha(id) ON DELETE RESTRICT,
  valor_aplicado numeric(14,2) NOT NULL CHECK (valor_aplicado > 0),
  confianca numeric(3,2) CHECK (confianca IS NULL OR (confianca BETWEEN 0 AND 1)),
  origem origem_conciliacao NOT NULL,
  aprovada_por uuid REFERENCES usuario(id),
  aprovada_em timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_conc_tx ON conciliacao_orcamento(transacao_id);
CREATE INDEX idx_conc_linha ON conciliacao_orcamento(orcamento_linha_id);

-- ============================================================
-- Tabela: regra_classificacao (aprendizado)
-- ============================================================
CREATE TABLE regra_classificacao (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  titular_pix_padrao text NOT NULL,
  orcamento_linha_id uuid REFERENCES orcamento_linha(id) ON DELETE SET NULL,
  categoria_id uuid REFERENCES categoria_despesa(id),
  projeto_id uuid REFERENCES projeto(id),
  empresa_id uuid REFERENCES empresa(id),
  confianca_base numeric(3,2) NOT NULL DEFAULT 0.95 CHECK (confianca_base BETWEEN 0 AND 1),
  uso_count integer NOT NULL DEFAULT 0,
  ativa boolean NOT NULL DEFAULT true,
  criada_por uuid REFERENCES usuario(id),
  criada_em timestamptz NOT NULL DEFAULT now(),
  ultima_utilizacao timestamptz
);
CREATE INDEX idx_regra_titular ON regra_classificacao(lower(titular_pix_padrao))
  WHERE ativa = true;
CREATE UNIQUE INDEX ux_regra_titular_ativa
  ON regra_classificacao(lower(titular_pix_padrao))
  WHERE ativa = true;

-- ============================================================
-- Extensões em tabelas existentes
-- ============================================================

-- transacao_bancaria: origem_banco e natureza_lancamento
ALTER TABLE transacao_bancaria
  ADD COLUMN origem_banco origem_banco,
  ADD COLUMN natureza_lancamento natureza_lancamento;

-- Backfill para transações já persistidas (são todas Bradesco até aqui):
UPDATE transacao_bancaria
SET origem_banco = 'BRADESCO',
    natureza_lancamento = 'PIX_DEBITO'
WHERE origem_banco IS NULL;

-- Tornar NOT NULL após backfill
ALTER TABLE transacao_bancaria
  ALTER COLUMN origem_banco SET NOT NULL;

-- registro_pp: FK opcional para orcamento_linha (natureza PROFISSIONAIS)
ALTER TABLE registro_pp
  ADD COLUMN orcamento_linha_id uuid REFERENCES orcamento_linha(id) ON DELETE SET NULL;
CREATE INDEX idx_registro_pp_orcamento_linha ON registro_pp(orcamento_linha_id)
  WHERE orcamento_linha_id IS NOT NULL;

-- adiantamento: lifecycle de compensação
ALTER TABLE adiantamento
  ADD COLUMN status adiantamento_status NOT NULL DEFAULT 'ABERTO',
  ADD COLUMN compensado_em_registro_pp_id uuid REFERENCES registro_pp(id) ON DELETE SET NULL,
  ADD COLUMN compensado_em timestamptz;
CREATE INDEX idx_adiantamento_status ON adiantamento(status)
  WHERE status = 'ABERTO';

-- ============================================================
-- RLS das tabelas novas
-- ============================================================
ALTER TABLE conciliacao_orcamento ENABLE ROW LEVEL SECURITY;
ALTER TABLE regra_classificacao ENABLE ROW LEVEL SECURITY;

CREATE POLICY conc_select ON conciliacao_orcamento FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY conc_insert ON conciliacao_orcamento FOR INSERT WITH CHECK (auth.uid() IS NOT NULL AND aprovada_por = auth.uid());
CREATE POLICY conc_delete ON conciliacao_orcamento FOR DELETE USING (auth.uid() IS NOT NULL);

CREATE POLICY regra_select ON regra_classificacao FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY regra_insert ON regra_classificacao FOR INSERT WITH CHECK (auth.uid() IS NOT NULL AND criada_por = auth.uid());
CREATE POLICY regra_update ON regra_classificacao FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY regra_delete ON regra_classificacao FOR DELETE USING (fn_is_ceo());

-- ============================================================
-- Triggers auditoria
-- ============================================================
CREATE TRIGGER trg_audit_conciliacao AFTER INSERT OR UPDATE OR DELETE ON conciliacao_orcamento
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();
CREATE TRIGGER trg_audit_regra AFTER INSERT OR UPDATE OR DELETE ON regra_classificacao
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

-- ============================================================
-- Grants
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON conciliacao_orcamento, regra_classificacao TO authenticated;
