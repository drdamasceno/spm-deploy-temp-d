-- Migration 0019: adiciona RECEITA_FINANCEIRA ao enum natureza_lancamento.
--
-- NOTA: ALTER TYPE ADD VALUE não pode rodar em transação (igual migration 0014).
-- Aplicar como comando isolado.

ALTER TYPE natureza_lancamento ADD VALUE IF NOT EXISTS 'RECEITA_FINANCEIRA';
