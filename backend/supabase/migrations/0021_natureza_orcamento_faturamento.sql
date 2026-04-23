-- Migration 0021: adiciona FATURAMENTO ao enum natureza_orcamento
-- (não confundir com natureza_lancamento, que é de transacao_bancaria e
-- já recebeu FATURAMENTO na 0020 por engano — ambos os enums precisam).
--
-- Origem: refator do parser do XLSX para a seção "Despesas de Profissionais"
-- gerar DUAS linhas de orcamento_linha por registro:
--   - DESPESA_PROFISSIONAIS (valor = coluna DESPESAS / G)
--   - FATURAMENTO           (valor = coluna RECEITA  / F)
--
-- NOTA: ALTER TYPE ADD VALUE não pode rodar em transação.

ALTER TYPE natureza_orcamento ADD VALUE IF NOT EXISTS 'FATURAMENTO';
