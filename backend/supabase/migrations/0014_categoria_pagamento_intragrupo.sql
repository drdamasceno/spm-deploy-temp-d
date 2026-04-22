-- Migration 0014: adiciona PAGAMENTO_INTRAGRUPO ao enum categoria_conciliacao
-- Semântica: SPM → empresa do grupo (ex: FD GESTAO) é despesa operacional
-- real (NFE emitida), não transferência interna.
--
-- Diferença:
--   TRANSFERENCIA_INTERNA: SPM Bradesco ↔ SPM Unicred (mesma empresa, caixa
--     consolidado não muda). FILTRADA do Dashboard.
--   PAGAMENTO_INTRAGRUPO: SPM → FD GESTAO (empresa distinta do grupo, NFE,
--     despesa real). CONTA no Dashboard. Fica fora do pool de sugestões
--     para evitar match falso contra prestador individual do PP.
--
-- NOTA: ALTER TYPE ADD VALUE não pode rodar dentro de transação (BEGIN/COMMIT)
-- em PostgreSQL. Aplicar como comando isolado.

ALTER TYPE categoria_conciliacao ADD VALUE IF NOT EXISTS 'PAGAMENTO_INTRAGRUPO';

-- Backfill: reclassifica transações SPM → FD que estavam erroneamente
-- marcadas como TRANSFERENCIA_INTERNA.
-- (Aplicado manualmente em 2026-04-22; deixado aqui para rerodar em
-- ambiente limpo.)
-- UPDATE transacao_bancaria SET categoria = 'PAGAMENTO_INTRAGRUPO'
-- WHERE categoria = 'TRANSFERENCIA_INTERNA' AND UPPER(descricao) LIKE '%FD GESTAO%';
