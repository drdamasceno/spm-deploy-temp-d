-- Migration 0017: tabela transacao_linha permite split de uma transação em
-- N alocações (ex: fatura de cartão metade SPM, metade pessoal).
--
-- Invariante: sum(transacao_linha.valor) = transacao_bancaria.valor da tx pai.
-- Validação feita no router (permite estados temporários durante edição).

BEGIN;

CREATE TABLE transacao_linha (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  transacao_bancaria_id uuid NOT NULL REFERENCES transacao_bancaria(id) ON DELETE CASCADE,
  valor numeric(14,2) NOT NULL CHECK (valor <> 0),
  bolso bolso_tipo NOT NULL,
  orcamento_linha_id uuid REFERENCES orcamento_linha(id),
  empresa_pagadora_id uuid REFERENCES empresa(id),
  descricao text,
  criado_em timestamptz NOT NULL DEFAULT now(),
  criado_por uuid REFERENCES auth.users(id)
);

CREATE INDEX idx_transacao_linha_transacao ON transacao_linha(transacao_bancaria_id);
CREATE INDEX idx_transacao_linha_bolso ON transacao_linha(bolso);
CREATE INDEX idx_transacao_linha_orcamento
  ON transacao_linha(orcamento_linha_id)
  WHERE orcamento_linha_id IS NOT NULL;

ALTER TABLE transacao_linha ENABLE ROW LEVEL SECURITY;

CREATE POLICY transacao_linha_select ON transacao_linha
  FOR SELECT USING (auth.uid() IS NOT NULL);

CREATE POLICY transacao_linha_insert ON transacao_linha
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY transacao_linha_update ON transacao_linha
  FOR UPDATE USING (auth.uid() IS NOT NULL);

CREATE POLICY transacao_linha_delete ON transacao_linha
  FOR DELETE USING (auth.uid() IS NOT NULL);

CREATE TRIGGER trg_audit_transacao_linha
  AFTER INSERT OR UPDATE OR DELETE ON transacao_linha
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

COMMIT;
