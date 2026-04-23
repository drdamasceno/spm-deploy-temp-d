-- Migration 0016: enum bolso_tipo + coluna bolso em orcamento_linha,
-- mais coluna empresa_pagadora_id (FK opcional para empresa).
--
-- Bolso é dimensão gerencial ortogonal à natureza (spec §3.1).
-- Quatro valores fixos conhecidos → enum, não tabela lookup.
-- Default SPM_OPERACIONAL preserva comportamento atual.

BEGIN;

CREATE TYPE bolso_tipo AS ENUM (
  'SPM_OPERACIONAL',
  'FD_VIA_SPM',
  'HUGO_PESSOAL',
  'INVESTIMENTO_HUGO'
);

ALTER TABLE orcamento_linha
  ADD COLUMN bolso bolso_tipo NOT NULL DEFAULT 'SPM_OPERACIONAL',
  ADD COLUMN empresa_pagadora_id uuid REFERENCES empresa(id);

CREATE INDEX idx_orcamento_linha_bolso ON orcamento_linha(bolso);
CREATE INDEX idx_orcamento_linha_empresa_pagadora
  ON orcamento_linha(empresa_pagadora_id)
  WHERE empresa_pagadora_id IS NOT NULL;

COMMIT;
