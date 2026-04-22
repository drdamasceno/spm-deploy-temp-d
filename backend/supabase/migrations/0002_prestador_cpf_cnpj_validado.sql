-- 0002_prestador_cpf_cnpj_validado.sql
-- Passo 2 do plano v1 — suporte a seed de prestadores cuja chave PIX nao e CPF/CNPJ
-- (Telefone, Email, Aleatoria). Para esses, cpf_cnpj fica com placeholder
-- 'PENDENTE:PIX_<TIPO>:<CHAVE>' e cpf_cnpj_validado = false.
-- Quando Hugo carregar o relatorio de dados pessoais completo via UI, o
-- cpf_cnpj real substitui o placeholder e cpf_cnpj_validado passa a true.

ALTER TABLE prestador
  ADD COLUMN cpf_cnpj_validado boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN prestador.cpf_cnpj_validado IS
  'true quando cpf_cnpj tem formato valido de CPF ou CNPJ. false quando e placeholder PENDENTE:PIX_<TIPO>:<CHAVE> — dado ausente no PP e pendente de atualizacao manual.';
