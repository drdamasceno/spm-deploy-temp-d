-- Migration 0011: saldos (contas correntes + aplicações financeiras)
-- Track D: dashboard de liquidez

BEGIN;

-- ========================================================
-- Tabela: saldo_conta_snapshot (contas correntes)
-- ========================================================
CREATE TYPE origem_saldo AS ENUM ('BRADESCO_OFX', 'UNICRED_PDF', 'MANUAL');

CREATE TABLE saldo_conta_snapshot (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conta_bancaria_id uuid NOT NULL REFERENCES conta_bancaria(id) ON DELETE CASCADE,
  saldo_valor numeric(14,2) NOT NULL,
  data_referencia date NOT NULL,
  origem origem_saldo NOT NULL,
  observacao text,
  criado_em timestamptz NOT NULL DEFAULT now(),
  criado_por uuid REFERENCES usuario(id)
);

CREATE INDEX idx_snapshot_conta_data ON saldo_conta_snapshot (conta_bancaria_id, data_referencia DESC);

-- ========================================================
-- Tabela: aplicacao_financeira
-- ========================================================
CREATE TYPE tipo_aplicacao AS ENUM (
  'CDB', 'LCA', 'LCI', 'FUNDO', 'POUPANCA',
  'TESOURO', 'ACOES', 'FII', 'OUTROS'
);

CREATE TYPE modo_aplicacao AS ENUM ('AUTOMATICA', 'MANUAL');

CREATE TYPE liquidez_aplicacao AS ENUM ('DIARIA', 'VENCIMENTO', 'D30', 'D90', 'D180');

CREATE TABLE aplicacao_financeira (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome text NOT NULL,
  tipo tipo_aplicacao NOT NULL,
  valor_atual numeric(14,2) NOT NULL DEFAULT 0,
  data_atualizacao date NOT NULL DEFAULT CURRENT_DATE,
  modo modo_aplicacao NOT NULL,
  instituicao text,
  rentabilidade text,
  data_vencimento date,
  liquidez liquidez_aplicacao,
  observacoes text,
  ativo boolean NOT NULL DEFAULT true,
  criado_em timestamptz NOT NULL DEFAULT now(),
  updated_em timestamptz NOT NULL DEFAULT now(),
  criado_por uuid REFERENCES usuario(id)
);

CREATE INDEX idx_aplicacao_ativo ON aplicacao_financeira (ativo) WHERE ativo = true;

-- ========================================================
-- Tabela: aplicacao_historico (snapshots de valor ao longo do tempo)
-- ========================================================
CREATE TABLE aplicacao_historico (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  aplicacao_id uuid NOT NULL REFERENCES aplicacao_financeira(id) ON DELETE CASCADE,
  valor numeric(14,2) NOT NULL,
  data_snapshot date NOT NULL,
  criado_em timestamptz NOT NULL DEFAULT now(),
  criado_por uuid REFERENCES usuario(id)
);

CREATE INDEX idx_historico_aplicacao_data ON aplicacao_historico (aplicacao_id, data_snapshot DESC);

-- ========================================================
-- Trigger: quando valor_atual muda, salva snapshot histórico automaticamente
-- ========================================================
CREATE OR REPLACE FUNCTION fn_aplicacao_historico_trigger()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') OR (TG_OP = 'UPDATE' AND NEW.valor_atual IS DISTINCT FROM OLD.valor_atual) THEN
    INSERT INTO aplicacao_historico (aplicacao_id, valor, data_snapshot, criado_por)
    VALUES (NEW.id, NEW.valor_atual, NEW.data_atualizacao, NEW.criado_por);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_aplicacao_historico
  AFTER INSERT OR UPDATE ON aplicacao_financeira
  FOR EACH ROW EXECUTE FUNCTION fn_aplicacao_historico_trigger();

-- ========================================================
-- RLS
-- ========================================================
ALTER TABLE saldo_conta_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE aplicacao_financeira ENABLE ROW LEVEL SECURITY;
ALTER TABLE aplicacao_historico ENABLE ROW LEVEL SECURITY;

CREATE POLICY saldo_conta_snapshot_all ON saldo_conta_snapshot FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY aplicacao_financeira_all ON aplicacao_financeira FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY aplicacao_historico_all ON aplicacao_historico FOR ALL USING (true) WITH CHECK (true);

COMMIT;
