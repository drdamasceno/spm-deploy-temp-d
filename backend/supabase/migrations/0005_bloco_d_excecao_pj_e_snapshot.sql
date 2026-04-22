-- =============================================================================
-- Migration 0005 — Bloco D: CRUD excecao_pj + rodada_snapshot
-- =============================================================================
-- Versão: 2026-04-20 (revisada após review do Claude Code)
--
-- Ajustes desta versão:
--   [1] fn_bloqueia_rodada_aprovada: RETURN com CASE para DELETE vs UPDATE
--   [2] CHECK ck_rodada_aprovacao_coerente: impede aprovação sem snapshot
--   [3] CHECK 0-100 em percentual_conciliado
--
-- Fora do escopo (backlog):
--   - Hash SHA256 via trigger pgcrypto (endurecimento futuro, Victor)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Parte 1: endurecer policies de excecao_pj
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS excecao_pj_insert ON excecao_pj;
DROP POLICY IF EXISTS excecao_pj_update ON excecao_pj;

CREATE POLICY excecao_pj_insert ON excecao_pj
  FOR INSERT
  WITH CHECK (fn_is_ceo());

CREATE POLICY excecao_pj_update ON excecao_pj
  FOR UPDATE
  USING (fn_is_ceo())
  WITH CHECK (fn_is_ceo());


-- -----------------------------------------------------------------------------
-- Parte 2: UNIQUE parcial em excecao_pj
-- -----------------------------------------------------------------------------

CREATE UNIQUE INDEX ux_excecao_pj_prestador_cnpj_ativo
  ON excecao_pj (prestador_id, cnpj)
  WHERE ativo = true AND cnpj IS NOT NULL;


-- -----------------------------------------------------------------------------
-- Parte 3: tabela rodada_snapshot
-- -----------------------------------------------------------------------------

CREATE TABLE rodada_snapshot (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rodada_id uuid NOT NULL REFERENCES rodada(id) ON DELETE RESTRICT,
  aprovada_em timestamptz NOT NULL DEFAULT now(),
  aprovada_por uuid NOT NULL REFERENCES usuario(id),

  total_pp_elegivel numeric(14,2) NOT NULL,
  total_conciliado numeric(14,2) NOT NULL,
  percentual_conciliado numeric(5,2) NOT NULL
    CHECK (percentual_conciliado BETWEEN 0 AND 100),
  qtd_transacoes integer NOT NULL CHECK (qtd_transacoes >= 0),
  qtd_registros_pp integer NOT NULL CHECK (qtd_registros_pp >= 0),

  payload jsonb NOT NULL,
  hash_payload text NOT NULL,

  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ux_rodada_snapshot_rodada ON rodada_snapshot (rodada_id);
CREATE INDEX idx_rodada_snapshot_aprovada_em ON rodada_snapshot (aprovada_em DESC);


-- -----------------------------------------------------------------------------
-- Parte 4: RLS de rodada_snapshot
-- -----------------------------------------------------------------------------

ALTER TABLE rodada_snapshot ENABLE ROW LEVEL SECURITY;

CREATE POLICY rodada_snapshot_select ON rodada_snapshot
  FOR SELECT
  USING (auth.uid() IS NOT NULL);

CREATE POLICY rodada_snapshot_insert ON rodada_snapshot
  FOR INSERT
  WITH CHECK (fn_is_ceo());

-- UPDATE: sem policy = negado com RLS ativo
-- DELETE: sem policy = negado com RLS ativo


-- -----------------------------------------------------------------------------
-- Parte 5: trigger de auditoria em rodada_snapshot
-- -----------------------------------------------------------------------------

CREATE TRIGGER trg_audit_rodada_snapshot
  AFTER INSERT ON rodada_snapshot
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();


-- -----------------------------------------------------------------------------
-- Parte 6: colunas de aprovação em rodada
-- -----------------------------------------------------------------------------

ALTER TABLE rodada
  ADD COLUMN IF NOT EXISTS snapshot_id uuid REFERENCES rodada_snapshot(id),
  ADD COLUMN IF NOT EXISTS aprovada_em timestamptz,
  ADD COLUMN IF NOT EXISTS aprovada_por uuid REFERENCES usuario(id);

CREATE INDEX IF NOT EXISTS idx_rodada_aprovada
  ON rodada (aprovada_em)
  WHERE aprovada_em IS NOT NULL;


-- -----------------------------------------------------------------------------
-- Parte 6.1: CHECK de coerência de aprovação
-- -----------------------------------------------------------------------------
-- Impede aprovação via SQL direto sem snapshot. Três colunas devem ser NULL
-- juntas ou NOT NULL juntas. Fecha brecha de UPDATE manual.

ALTER TABLE rodada ADD CONSTRAINT ck_rodada_aprovacao_coerente
  CHECK (
    (aprovada_em IS NULL AND snapshot_id IS NULL AND aprovada_por IS NULL)
    OR
    (aprovada_em IS NOT NULL AND snapshot_id IS NOT NULL AND aprovada_por IS NOT NULL)
  );


-- -----------------------------------------------------------------------------
-- Parte 7: trigger que impede UPDATE/DELETE em rodada aprovada
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_bloqueia_rodada_aprovada()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.aprovada_em IS NOT NULL THEN
    RAISE EXCEPTION 'Rodada % já foi aprovada em % e é imutável. Operação bloqueada.',
      OLD.id, OLD.aprovada_em;
  END IF;
  -- Correção: DELETE trigger não pode retornar NEW (é NULL).
  -- UPDATE retorna NEW; DELETE retorna OLD.
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bloqueia_update_rodada_aprovada
  BEFORE UPDATE ON rodada
  FOR EACH ROW
  WHEN (OLD.aprovada_em IS NOT NULL)
  EXECUTE FUNCTION fn_bloqueia_rodada_aprovada();

CREATE TRIGGER trg_bloqueia_delete_rodada_aprovada
  BEFORE DELETE ON rodada
  FOR EACH ROW
  WHEN (OLD.aprovada_em IS NOT NULL)
  EXECUTE FUNCTION fn_bloqueia_rodada_aprovada();


-- =============================================================================
-- Fim da migration 0005
-- =============================================================================
-- Backlog (endurecimento futuro — Victor):
--   - CREATE EXTENSION pgcrypto
--   - Trigger BEFORE INSERT em rodada_snapshot recalculando hash_payload
--     via encode(digest(payload::text, 'sha256'), 'hex') e comparando com
--     o valor enviado pela API. Bloqueia se divergir.
-- =============================================================================
