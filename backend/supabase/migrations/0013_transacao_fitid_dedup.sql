-- Migration 0013: fitid em transacao_bancaria + unique parcial pra dedup
BEGIN;
ALTER TABLE transacao_bancaria ADD COLUMN fitid text;
CREATE UNIQUE INDEX ux_transacao_conta_fitid
  ON transacao_bancaria (conta_id, fitid)
  WHERE fitid IS NOT NULL;
COMMIT;
