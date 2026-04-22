-- Passo 3 - Migration de schema
-- Cria tabela rodada e adiciona colunas necessarias para persistir conciliacao

CREATE TABLE rodada (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  periodo_extrato_inicio date NOT NULL,
  periodo_extrato_fim date NOT NULL,
  pp_competencias text[] NOT NULL,
  criado_por uuid REFERENCES usuario(id),
  criado_em timestamptz NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'CRIADA'
    CHECK (status IN ('CRIADA', 'PROCESSANDO', 'CONCILIADA', 'VALIDADA', 'CANCELADA'))
);

-- Regra [ANCORADA] 23: pp_competencias e array porque o motor precisa
-- carregar PP do mes anterior ao mes do PIX alem do PP da rodada
-- (caso CLTs/coordenadora). Ex: rodada 93,5% = ARRAY['2026-02', '2026-03'].
COMMENT ON COLUMN rodada.pp_competencias IS
  'Array de competencias no formato YYYY-MM. Inclui o PP da rodada + PP do mes anterior ao PIX do extrato (regra [ANCORADA] 23).';

ALTER TABLE rodada ENABLE ROW LEVEL SECURITY;

-- SELECT: qualquer autenticado pode listar rodadas
CREATE POLICY rodada_select ON rodada FOR SELECT
  USING (auth.uid() IS NOT NULL);

-- INSERT: qualquer autenticado pode criar, mas identidade e obrigatoria
CREATE POLICY rodada_insert ON rodada FOR INSERT
  WITH CHECK (auth.uid() IS NOT NULL AND criado_por = auth.uid());

-- UPDATE: CEO sempre; demais usuarios so a propria rodada E so se nao
-- validada. Rodada com status='VALIDADA' e imutavel exceto pelo CEO.
CREATE POLICY rodada_update ON rodada FOR UPDATE
  USING (
    fn_is_ceo()
    OR (criado_por = auth.uid() AND status <> 'VALIDADA')
  )
  WITH CHECK (
    fn_is_ceo()
    OR (criado_por = auth.uid() AND status <> 'VALIDADA')
  );

-- DELETE: so CEO
CREATE POLICY rodada_delete ON rodada FOR DELETE
  USING (fn_is_ceo());

-- Associacao com registro_pp: RESTRICT para proteger o seed
-- (374 registros da rodada 93,5% sao transcricao literal — nao podem
-- desaparecer por DELETE inadvertido em rodada).
ALTER TABLE registro_pp
  ADD COLUMN rodada_id uuid REFERENCES rodada(id) ON DELETE RESTRICT;

-- Associacao com transacao_bancaria: SET NULL porque transacoes existem
-- independentemente da rodada em que foram conciliadas (sao dados do extrato).
ALTER TABLE transacao_bancaria
  ADD COLUMN rodada_id uuid REFERENCES rodada(id) ON DELETE SET NULL;

ALTER TABLE transacao_bancaria
  ADD COLUMN registro_pp_id uuid REFERENCES registro_pp(id) ON DELETE SET NULL;

CREATE INDEX idx_registro_pp_rodada ON registro_pp(rodada_id);
CREATE INDEX idx_transacao_bancaria_rodada ON transacao_bancaria(rodada_id);
CREATE INDEX idx_transacao_bancaria_registro_pp
  ON transacao_bancaria(registro_pp_id)
  WHERE registro_pp_id IS NOT NULL;
