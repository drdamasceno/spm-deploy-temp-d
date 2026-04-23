-- Migration 0018: saldo_caixa_diario (materialização para evolução do caixa
-- e tendência histórica) + colunas de rendimento em aplicacao_financeira
-- (precisão máxima: rendimento MANUAL sobrescreve CALCULADO).

BEGIN;

CREATE TABLE saldo_caixa_diario (
  data date NOT NULL,
  empresa_id uuid NOT NULL REFERENCES empresa(id),
  saldo_contas_correntes numeric(14,2) NOT NULL DEFAULT 0,
  saldo_aplicacoes numeric(14,2) NOT NULL DEFAULT 0,
  liquidez_total numeric(14,2)
    GENERATED ALWAYS AS (saldo_contas_correntes + saldo_aplicacoes) STORED,
  rendimento_do_dia numeric(14,2) NOT NULL DEFAULT 0,
  entradas_do_dia numeric(14,2) NOT NULL DEFAULT 0,
  saidas_do_dia numeric(14,2) NOT NULL DEFAULT 0,
  atualizado_em timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (data, empresa_id)
);

CREATE INDEX idx_saldo_caixa_diario_data ON saldo_caixa_diario(data DESC);

ALTER TABLE saldo_caixa_diario ENABLE ROW LEVEL SECURITY;

CREATE POLICY saldo_caixa_diario_select ON saldo_caixa_diario
  FOR SELECT USING (auth.uid() IS NOT NULL);

CREATE POLICY saldo_caixa_diario_all_ceo ON saldo_caixa_diario
  FOR ALL USING (fn_is_ceo());

CREATE TYPE fonte_rendimento AS ENUM ('CALCULADO', 'MANUAL');

ALTER TABLE aplicacao_financeira
  ADD COLUMN rendimento_ultima_atualizacao numeric(14,2),
  ADD COLUMN rendimento_ultima_atualizacao_fonte fonte_rendimento;

COMMIT;
