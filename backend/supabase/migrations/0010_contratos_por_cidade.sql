-- backend/supabase/migrations/0010_contratos_por_cidade.sql
-- Modelo: 1 contrato = 1 (uf, cidade). Consolida artefato do parser (115 → 15).

BEGIN;

-- Colunas novas em `contrato`
ALTER TABLE contrato ADD COLUMN uf text;
ALTER TABLE contrato ADD COLUMN cidade text;
ALTER TABLE contrato ADD COLUMN nome_oficial text;
ALTER TABLE contrato ADD COLUMN valor_faturamento_mensal numeric(14,2);
ALTER TABLE contrato ADD COLUMN retencao_tributaria_pct numeric(5,2);
ALTER TABLE contrato ADD COLUMN observacoes text;

-- `registro_pp` ganha local_pp (preserva sub-local pro detalhe)
ALTER TABLE registro_pp ADD COLUMN local_pp text;

-- Remove unique constraint incompatível com o novo modelo (1 contrato = 1 cidade,
-- mas 1 prestador pode ter N linhas na mesma cidade/mes por sub-local diferente)
ALTER TABLE registro_pp DROP CONSTRAINT registro_pp_prestador_id_contrato_id_mes_competencia_key;

-- Backfill uf + cidade do local_pp atual, normalizando separador `–` → `-`
UPDATE contrato
SET
  uf = upper(trim(split_part(regexp_replace(local_pp, '–', '-', 'g'), ' - ', 1))),
  cidade = upper(trim(split_part(regexp_replace(local_pp, '–', '-', 'g'), ' - ', 2)))
WHERE local_pp IS NOT NULL;

-- Backfill local_pp em registro_pp (tudo após "UF - CIDADE - ")
UPDATE registro_pp r
SET local_pp = sub.local_sub
FROM (
  SELECT c.id AS contrato_id,
    CASE
      WHEN array_length(string_to_array(regexp_replace(c.local_pp, '–', '-', 'g'), ' - '), 1) >= 3
      THEN array_to_string(
        (string_to_array(regexp_replace(c.local_pp, '–', '-', 'g'), ' - '))[3:],
        ' - '
      )
      ELSE NULL
    END AS local_sub
  FROM contrato c
) sub
WHERE r.contrato_id = sub.contrato_id;

-- Coluna cidade_norm (pra UNIQUE match sem acento)
ALTER TABLE contrato ADD COLUMN cidade_norm text;
UPDATE contrato SET cidade_norm =
  translate(upper(cidade),
    'ÃÁÀÂÄÉÊÈËÍÎÌÏÓÔÒÖÚÛÙÜÇÑ',
    'AAAAAEEEEIIIIOOOOUUUUCN');

-- Consolidação: pra cada (uf, cidade_norm), escolhe MIN(id::text) como principal (determinístico com UUID)
WITH principais AS (
  SELECT uf, cidade_norm, MIN(id::text)::uuid AS id_principal
  FROM contrato
  WHERE uf IS NOT NULL AND cidade_norm IS NOT NULL
  GROUP BY uf, cidade_norm
)
UPDATE registro_pp r
SET contrato_id = p.id_principal
FROM contrato c, principais p
WHERE r.contrato_id = c.id
  AND c.uf = p.uf
  AND c.cidade_norm = p.cidade_norm
  AND c.id != p.id_principal;

-- Deleta contratos duplicados
DELETE FROM contrato
WHERE id NOT IN (SELECT DISTINCT contrato_id FROM registro_pp WHERE contrato_id IS NOT NULL);

-- NOT NULL + UNIQUE
ALTER TABLE contrato ALTER COLUMN uf SET NOT NULL;
ALTER TABLE contrato ALTER COLUMN cidade SET NOT NULL;
ALTER TABLE contrato ALTER COLUMN cidade_norm SET NOT NULL;
CREATE UNIQUE INDEX unique_uf_cidade_norm ON contrato (uf, cidade_norm);

-- local_pp passa a viver em registro_pp, não em contrato
ALTER TABLE contrato DROP COLUMN local_pp;

COMMIT;
