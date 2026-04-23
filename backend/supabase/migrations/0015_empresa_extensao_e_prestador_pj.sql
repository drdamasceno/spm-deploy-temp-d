-- Migration 0015: amplia tabela empresa com regime_tributario e papel,
-- e adiciona prestador.pj_empregadora_id (FK opcional para empresa).
--
-- Decisão: em vez de criar tabela empresa_grupo nova (spec §3.1), estendemos
-- a tabela empresa existente. Menos redundância, aproveita RLS/infra.
--
-- SPM e FD já existem em empresa (migration 0007 + seeds posteriores).

BEGIN;

CREATE TYPE regime_tributario_empresa AS ENUM (
  'LUCRO_REAL',
  'LUCRO_PRESUMIDO',
  'SIMPLES_NACIONAL'
);

CREATE TYPE papel_empresa AS ENUM (
  'PRINCIPAL',
  'INTRAGRUPO'
);

ALTER TABLE empresa
  ADD COLUMN regime_tributario regime_tributario_empresa,
  ADD COLUMN papel papel_empresa;

UPDATE empresa SET
  regime_tributario = 'LUCRO_REAL',
  papel = 'PRINCIPAL'
WHERE codigo = 'SPM';

UPDATE empresa SET
  regime_tributario = 'SIMPLES_NACIONAL',
  papel = 'INTRAGRUPO'
WHERE codigo = 'FD';

ALTER TABLE empresa
  ALTER COLUMN regime_tributario SET NOT NULL,
  ALTER COLUMN papel SET NOT NULL;

ALTER TABLE prestador
  ADD COLUMN pj_empregadora_id uuid REFERENCES empresa(id);

CREATE INDEX idx_prestador_pj_empregadora
  ON prestador(pj_empregadora_id)
  WHERE pj_empregadora_id IS NOT NULL;

COMMIT;
