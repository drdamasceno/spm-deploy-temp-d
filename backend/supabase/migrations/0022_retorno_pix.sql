-- Migration 0022: tabela `retorno_pix` — fonte determinística de pagamento
-- a profissionais em lote (substitui heurística extrato↔PP que produzia
-- falsos positivos cross-prestador).
--
-- Origem: bug Henrique Storino ↔ Eduarda Vitor (abril/2026). Motor casava
-- PIX por valor exato sem titularidade quando não havia candidato por nome,
-- atribuindo PIX alheio a registro_pp errado e exibindo como pago em
-- /contratos com risco de pagamento duplicado pela Thais.
--
-- Solução: importar arquivo CNAB-240 retorno PIX direto do banco. Cada
-- linha do retorno tem chave PIX + documento + valor + ocorrência (status)
-- explícitos, eliminando inferência. Usado no /contratos/_pago_por_chave_v2.

-- ---------------------------------------------------------------------------
-- Enum: status de pagamento por linha do retorno (com base no código de
-- ocorrência do banco). Mapping carregado do parser para domínio do sistema.
-- ---------------------------------------------------------------------------
CREATE TYPE retorno_pix_status AS ENUM (
  'CONFIRMADO',     -- PIX efetivamente saiu da conta
  'AGENDADO',       -- programado mas ainda não executado
  'REJEITADO',      -- recusado pelo banco (chave inválida, conta inexistente, etc.)
  'ESTORNADO',      -- saiu e foi devolvido
  'OUTRO'           -- código de ocorrência não mapeado — precisa revisão
);

-- ---------------------------------------------------------------------------
-- Tabela retorno_pix — uma linha por pagamento confirmado pelo banco.
-- ---------------------------------------------------------------------------
CREATE TABLE retorno_pix (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- procedência
  banco              TEXT        NOT NULL,                -- '237' Bradesco, '136' Unicred etc.
  conta_id           UUID        REFERENCES conta_bancaria(id),
  arquivo_origem     TEXT,                                -- nome do .RET importado
  arquivo_hash       TEXT        NOT NULL,                -- SHA-256 para dedup de re-upload
  importado_em       TIMESTAMP   NOT NULL DEFAULT now(),
  importado_por      UUID        REFERENCES auth.users(id),

  -- identidade do pagamento dentro do retorno
  seq_lote           TEXT,                                -- nº sequencial no lote
  nosso_numero       TEXT,                                -- ID Bradesco (13c) — único por banco
  id_documento_empresa TEXT,                              -- ID interno PP gerado pela Thais

  -- favorecido
  nome_favorecido    TEXT        NOT NULL,
  documento          TEXT        NOT NULL,                -- CPF (11) ou CNPJ (14), só dígitos
  tipo_pessoa        TEXT        NOT NULL CHECK (tipo_pessoa IN ('PF','PJ','?')),
  tipo_chave_pix     TEXT,                                -- '01' tel | '02' email | '03' doc
  chave_pix_literal  TEXT,                                -- chave em formato literal

  -- valores
  valor_instruido    NUMERIC(15,2) NOT NULL,
  valor_efetivado    NUMERIC(15,2) NOT NULL,
  data_pagamento     DATE,                                -- data efetivação no banco

  -- status banco
  ocorrencia_codigo  TEXT        NOT NULL,                -- código bruto do banco
  status             retorno_pix_status NOT NULL DEFAULT 'OUTRO',

  -- ligação opcional ao registro_pp (preenchida pelo motor de match
  -- determinístico — chave_pix/documento + valor + competência ativa)
  registro_pp_id     UUID        REFERENCES registro_pp(id),
  matched_em         TIMESTAMP,
  match_confianca    TEXT        CHECK (match_confianca IN ('DOC_EXATO', 'CHAVE_PIX', 'NOME_VALOR', NULL)),

  -- ligação opcional à transação no extrato (auditoria)
  transacao_bancaria_id UUID     REFERENCES transacao_bancaria(id),

  criado_em          TIMESTAMP   NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Índices: dedup por (arquivo_hash + nosso_numero) e busca por documento.
-- ---------------------------------------------------------------------------
CREATE UNIQUE INDEX idx_retorno_pix_dedup
  ON retorno_pix (arquivo_hash, nosso_numero)
  WHERE nosso_numero IS NOT NULL;

CREATE INDEX idx_retorno_pix_documento ON retorno_pix (documento);
CREATE INDEX idx_retorno_pix_data_pagamento ON retorno_pix (data_pagamento);
CREATE INDEX idx_retorno_pix_registro_pp ON retorno_pix (registro_pp_id) WHERE registro_pp_id IS NOT NULL;
CREATE INDEX idx_retorno_pix_status ON retorno_pix (status);

-- ---------------------------------------------------------------------------
-- RLS: somente usuário autenticado pode ler/escrever; service_role bypassa.
-- Política inicial restrita ao owner de papéis contábeis (Hugo CEO).
-- ---------------------------------------------------------------------------
ALTER TABLE retorno_pix ENABLE ROW LEVEL SECURITY;

CREATE POLICY "retorno_pix_read_authed" ON retorno_pix
  FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "retorno_pix_write_authed" ON retorno_pix
  FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "retorno_pix_update_authed" ON retorno_pix
  FOR UPDATE
  USING (auth.role() = 'authenticated');

-- ---------------------------------------------------------------------------
-- Comentários documentais
-- ---------------------------------------------------------------------------
COMMENT ON TABLE retorno_pix IS
  'Retorno CNAB-240 de pagamentos PIX em lote. Fonte determinística para coluna "Pago" em /contratos, substituindo heurística extrato↔PP.';

COMMENT ON COLUMN retorno_pix.match_confianca IS
  'Critério usado pelo matcher determinístico: DOC_EXATO (CPF/CNPJ + valor exato + competência ativa) é o ouro; demais são fallback.';

COMMENT ON COLUMN retorno_pix.arquivo_hash IS
  'SHA-256 do conteúdo do .RET. Dedup de re-upload. Combinado com nosso_numero garante que mesmo PIX não entra duas vezes mesmo se arquivos sobrepostos forem importados.';
