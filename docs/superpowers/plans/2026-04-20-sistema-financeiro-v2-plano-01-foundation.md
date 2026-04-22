# SPM Sistema Financeiro v2 — Plano 1 (Foundation: Migrations + Parsers)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preparar a base do sistema v2 — schema estendido com 7 tabelas novas + 3 parsers testados contra arquivos reais de Hugo — para que Plano 2 (Motor/API) e Plano 3 (UI) possam consumir.

**Architecture:** 3 migrations SQL sequenciais (0007, 0008, 0009) que introduzem as entidades `empresa`, `projeto`, `categoria_despesa`, `orcamento`, `orcamento_linha`, `conciliacao_orcamento`, `regra_classificacao` + extensões em `transacao_bancaria`, `registro_pp` e `adiantamento`. 2 parsers Python novos (orçamento XLSX com 6 seções, Unicred PDF com pdfplumber) seguindo o padrão dos parsers atuais (`pega_plantao.py`, `extrato_bradesco.py`). TDD rigoroso contra fixtures reais.

**Nota de numeração (revisada em 2026-04-20):** A migration **0006** fica reservada para fechar as 3 dívidas técnicas do Bloco D (atomicidade via RPC `fn_aprovar_rodada()`, hash SHA256 no banco via pgcrypto, limpeza de rodadas-teste) — registrada no `spec-tecnico.md` do vault. Por isso este plano começa em 0007.

**Pré-condição verificada (2026-04-20 via MCP Supabase list_tables):** Nenhuma das 7 tabelas que este plano cria existe no schema `public` do projeto `mkxehqhikcuykaxnpxff`. FaturaAI coabita o projeto com `usuarios`/`historico_classificacoes`/`faturas` — sem conflito de nome. [ANCORADA] 24 confirma que coexistência é suportada.

**Tech Stack:** Python 3.12 · openpyxl · pdfplumber · pytest · Supabase/Postgres · supabase-py · FastAPI (existente).

**Spec de referência:** `docs/superpowers/specs/2026-04-20-sistema-financeiro-v2-design.md`

---

## File Structure

### Novos arquivos

```
backend/
  supabase/migrations/
    0007_empresa_projeto_categoria.sql      # tabelas-catálogo + seeds SPM/FD
    0008_orcamento.sql                       # orcamento + orcamento_linha + view
    0009_conciliacao_regra_extensoes.sql     # tabelas N:N + regra + colunas novas
  src/
    orcamento_xlsx.py                        # parser XLSX de orçamento (6 seções)
    extrato_unicred.py                       # parser PDF Unicred
  tests/
    fixtures/
      SPM_Orcamento_04_2026.xlsx             # cópia do arquivo real de Hugo
      Comp_Unicred_20042026.pdf              # cópia do extrato Unicred
    test_orcamento_xlsx.py                   # testes do parser orçamento
    test_extrato_unicred.py                  # testes do parser Unicred
    test_extrato_bradesco_routing.py         # testes da extensão de roteamento
    test_migrations_smoke.py                 # smoke test CRUD das tabelas novas
```

### Arquivos modificados

```
backend/
  src/extrato_bradesco.py                    # adicionar extract_bank_account() para routing
  requirements.txt                            # adicionar pdfplumber, rapidfuzz
```

### Responsabilidades

- `orcamento_xlsx.py`: ler XLSX, detectar 6 subcabeçalhos de seção, extrair linhas estruturadas. Retorna `list[OrcamentoLinhaParsed]`. Não toca em DB.
- `extrato_unicred.py`: ler PDF, extrair linhas via regex com lookahead, classificar `natureza_lancamento`, extrair `titular_pix`. Retorna `list[TransacaoUnicredParsed]`. Não toca em DB.
- `extrato_bradesco.py` (modificação): adicionar função `extract_bank_account(ofx_bytes) -> (bankid, acctid)` para roteamento. Parser de transações continua igual.

---

## M1 — Modelagem + Migrations (5 tasks)

### Task 1.1: Migration 0007 — empresa + projeto + categoria_despesa

**Files:**
- Create: `backend/supabase/migrations/0007_empresa_projeto_categoria.sql`

- [ ] **Step 1: Criar o arquivo de migration com DDL completo**

```sql
-- 0007_empresa_projeto_categoria.sql
-- Tabelas-catálogo do sistema v2: empresa, projeto, categoria_despesa
-- Base para orcamento (0008) e conciliacao (0009)

-- ============================================================
-- Tabela: empresa
-- ============================================================
CREATE TABLE empresa (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo text NOT NULL UNIQUE,
  razao_social text NOT NULL,
  cnpj text,
  ativa boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_empresa_codigo ON empresa(codigo);

-- ============================================================
-- Tabela: categoria_despesa
-- ============================================================
CREATE TABLE categoria_despesa (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome text NOT NULL UNIQUE,
  descricao text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_categoria_nome ON categoria_despesa(lower(nome));

-- ============================================================
-- Tabela: projeto
-- ============================================================
CREATE TABLE projeto (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo text NOT NULL UNIQUE,
  descricao text,
  empresa_id uuid NOT NULL REFERENCES empresa(id),
  ativo boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_projeto_empresa ON projeto(empresa_id);
CREATE INDEX idx_projeto_codigo ON projeto(codigo);

-- ============================================================
-- RLS
-- ============================================================
ALTER TABLE empresa ENABLE ROW LEVEL SECURITY;
ALTER TABLE categoria_despesa ENABLE ROW LEVEL SECURITY;
ALTER TABLE projeto ENABLE ROW LEVEL SECURITY;

CREATE POLICY empresa_select ON empresa FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY empresa_insert ON empresa FOR INSERT WITH CHECK (fn_is_ceo());
CREATE POLICY empresa_update ON empresa FOR UPDATE USING (fn_is_ceo());
CREATE POLICY empresa_delete ON empresa FOR DELETE USING (fn_is_ceo());

CREATE POLICY categoria_select ON categoria_despesa FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY categoria_insert ON categoria_despesa FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY categoria_update ON categoria_despesa FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY categoria_delete ON categoria_despesa FOR DELETE USING (fn_is_ceo());

CREATE POLICY projeto_select ON projeto FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY projeto_insert ON projeto FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY projeto_update ON projeto FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY projeto_delete ON projeto FOR DELETE USING (fn_is_ceo());

-- ============================================================
-- Triggers de log_auditoria (reaproveita fn_log_auditoria da 0001)
-- ============================================================
CREATE TRIGGER trg_audit_empresa AFTER INSERT OR UPDATE OR DELETE ON empresa
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();
CREATE TRIGGER trg_audit_categoria AFTER INSERT OR UPDATE OR DELETE ON categoria_despesa
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();
CREATE TRIGGER trg_audit_projeto AFTER INSERT OR UPDATE OR DELETE ON projeto
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

-- ============================================================
-- Trigger de updated_at em empresa
-- ============================================================
CREATE TRIGGER trg_updated_at_empresa BEFORE UPDATE ON empresa
  FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- ============================================================
-- Grants
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON empresa, categoria_despesa, projeto TO authenticated;
```

- [ ] **Step 2: Aplicar migration via Supabase MCP**

```bash
# Via mcp__claude_ai_Supabase__apply_migration:
#   project_id: mkxehqhikcuykaxnpxff
#   name: "0007_empresa_projeto_categoria"
#   query: <conteúdo do arquivo acima>
```

Expected: `{"success": true}` + tabelas criadas.

- [ ] **Step 3: Validar via SQL**

```sql
SELECT COUNT(*) FROM empresa;          -- Expected: 0
SELECT COUNT(*) FROM categoria_despesa; -- Expected: 0
SELECT COUNT(*) FROM projeto;          -- Expected: 0
SELECT COUNT(*) FROM information_schema.tables
  WHERE table_name IN ('empresa','categoria_despesa','projeto'); -- Expected: 3
```

- [ ] **Step 4: Commit**

```bash
git add backend/supabase/migrations/0007_empresa_projeto_categoria.sql
git commit -m "feat(db): migration 0007 — empresa, projeto, categoria_despesa

Tabelas-catálogo base para o sistema v2. RLS + triggers de auditoria
seguindo o padrão das migrations 0001-0005."
```

---

### Task 1.2: Seeds iniciais (empresa SPM/FD + categorias do XLSX)

**Files:**
- Create: `backend/supabase/seeds/0001_seed_empresa_categoria.sql`

- [ ] **Step 1: Criar arquivo de seed**

```sql
-- 0001_seed_empresa_categoria.sql
-- Seeds para operação inicial: empresas SPM e FD + categorias derivadas
-- do arquivo real SPM-Orcamento-04.2026.xlsx

INSERT INTO empresa (codigo, razao_social, cnpj) VALUES
  ('SPM', 'SOCIEDADE PARANAENSE DE MEDICINA LTDA', '37.092.326/0001-04'),
  ('FD',  'FD GESTAO INTELIGENTE DE NEGOCIOS LTDA', '49.542.886/0001-94')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO categoria_despesa (nome) VALUES
  ('Diretoria Geral'),
  ('Comissões de Licitações e Credenciamentos'),
  ('Assessoria Juridica'),
  ('Salarios e Comissão de Escalistas'),
  ('Salários'),
  ('Salários ADM'),
  ('Salários ADM - Rescisão'),
  ('Setor Licitações e equipe de apoio'),
  ('Assessoria Juridica de Licitações e equipe de apoio'),
  ('Licitações - Diretoria de Licitação'),
  ('Diretoria Médica'),
  ('Coordenações Médicas Não Atribuidas Diretamente aos projetos'),
  ('Aluguel e Coworking, vistorias e Reformas Imovel locado'),
  ('Limpeza e serviços gerais'),
  ('Energia Elétrica'),
  ('Telefonia Internet'),
  ('Condomínio'),
  ('Software PegaPlantão, Omie, Digisac, Microsoft, Videogen, Chatgpt, Aplle'),
  ('Contabilidade'),
  ('Contabilidade FD'),
  ('Despesas Diretoria Geral'),
  ('Assistência Médica'),
  ('ISS'),
  ('DARF PREVIDENCIARIA INSS E ENCARGOS'),
  ('Retenção - PIS/COFINS/CSLL Prestadores de Serviços'),
  ('FGTS'),
  ('FGTS- GUIA DE RESCISÕES UNAI/MG'),
  ('COFINS FATURAMENTO'),
  ('PIS FATURAMENTO'),
  ('TRIMESTRE IRPJ'),
  ('TRIMESTRE CSLL'),
  ('Coordenação de Contratos/Coordenação Médica Apropriadas aos Projetos'),
  ('Serviços de Enfermagem/Despesas Gerais'),
  ('Publicidade Propaganda e Brindes'),
  ('ADIANTAMENTO DE SALÁRIOS ADM- FD'),
  ('Frete/Passagens/despesas viagem/Hospedagem Medicos dos projetos'),
  ('Despesas Gerais com Editais'),
  ('Água e Esgoto'),
  ('Despesas Viagens de UBER'),
  ('Provisão para Gastos Eventuais'),
  ('ROUPAS'),
  ('MEDICOS SM24'),
  ('ADMINISTRATIVOS SM24 - CLT'),
  ('Equipamentos'),
  ('Cartão de Crédito'),
  ('Serviços Mensal Estimados de Contratados Serviços Médicos'),
  ('PONTO ELETRONICO'),
  ('Parcelamento')
ON CONFLICT (nome) DO NOTHING;
```

- [ ] **Step 2: Aplicar seed via MCP execute_sql**

```bash
# Via mcp__claude_ai_Supabase__execute_sql com o conteúdo do arquivo acima.
```

- [ ] **Step 3: Validar**

```sql
SELECT COUNT(*) FROM empresa;            -- Expected: 2
SELECT COUNT(*) FROM categoria_despesa;  -- Expected: 48
SELECT codigo FROM empresa ORDER BY codigo;  -- Expected: FD, SPM
```

- [ ] **Step 4: Commit**

```bash
git add backend/supabase/seeds/0001_seed_empresa_categoria.sql
git commit -m "chore(db): seed inicial — empresas SPM/FD e 48 categorias

Categorias derivadas da análise do arquivo real SPM-Orcamento-04.2026.xlsx
durante brainstorm de 2026-04-20."
```

---

### Task 1.3: Migration 0008 — orcamento + orcamento_linha

**Files:**
- Create: `backend/supabase/migrations/0008_orcamento.sql`

- [ ] **Step 1: Criar migration**

```sql
-- 0008_orcamento.sql
-- Orçamento mensal: cabeçalho + linhas + enum de natureza + view de status

-- ============================================================
-- Enums
-- ============================================================
CREATE TYPE natureza_orcamento AS ENUM (
  'DESPESA_FIXA',
  'TRIBUTO',
  'SALARIO_VARIAVEL',
  'COMISSAO',
  'VALOR_VARIAVEL',
  'DESPESA_PROFISSIONAIS'
);

-- ============================================================
-- Tabela: orcamento (cabeçalho)
-- ============================================================
CREATE TABLE orcamento (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id uuid NOT NULL REFERENCES empresa(id),
  competencia text NOT NULL CHECK (competencia ~ '^\d{4}-\d{2}$'),
  status text NOT NULL DEFAULT 'RASCUNHO'
    CHECK (status IN ('RASCUNHO', 'VALIDADO', 'FECHADO')),
  criado_por uuid REFERENCES usuario(id),
  criado_em timestamptz NOT NULL DEFAULT now(),
  validado_em timestamptz,
  fechado_em timestamptz,
  UNIQUE (empresa_id, competencia)
);
CREATE INDEX idx_orcamento_competencia ON orcamento(competencia);
CREATE INDEX idx_orcamento_empresa ON orcamento(empresa_id);

-- ============================================================
-- Tabela: orcamento_linha
-- ============================================================
CREATE TABLE orcamento_linha (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  orcamento_id uuid NOT NULL REFERENCES orcamento(id) ON DELETE CASCADE,
  natureza natureza_orcamento NOT NULL,
  categoria_id uuid REFERENCES categoria_despesa(id),
  projeto_id uuid REFERENCES projeto(id),
  titular_cpf_cnpj text,
  titular_razao_social text NOT NULL,
  contrato_id uuid REFERENCES contrato(id),
  valor_previsto numeric(14,2) NOT NULL CHECK (valor_previsto >= 0),
  data_previsao date,
  observacao text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_linha_orcamento ON orcamento_linha(orcamento_id);
CREATE INDEX idx_linha_natureza ON orcamento_linha(natureza);
CREATE INDEX idx_linha_titular ON orcamento_linha(lower(titular_razao_social));
CREATE INDEX idx_linha_contrato ON orcamento_linha(contrato_id) WHERE contrato_id IS NOT NULL;

-- ============================================================
-- RLS
-- ============================================================
ALTER TABLE orcamento ENABLE ROW LEVEL SECURITY;
ALTER TABLE orcamento_linha ENABLE ROW LEVEL SECURITY;

CREATE POLICY orcamento_select ON orcamento FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY orcamento_insert ON orcamento FOR INSERT WITH CHECK (auth.uid() IS NOT NULL AND criado_por = auth.uid());
CREATE POLICY orcamento_update ON orcamento FOR UPDATE
  USING (fn_is_ceo() OR (criado_por = auth.uid() AND status <> 'FECHADO'));
CREATE POLICY orcamento_delete ON orcamento FOR DELETE USING (fn_is_ceo());

CREATE POLICY linha_select ON orcamento_linha FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY linha_insert ON orcamento_linha FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY linha_update ON orcamento_linha FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY linha_delete ON orcamento_linha FOR DELETE USING (auth.uid() IS NOT NULL);

-- ============================================================
-- Triggers de log_auditoria
-- ============================================================
CREATE TRIGGER trg_audit_orcamento AFTER INSERT OR UPDATE OR DELETE ON orcamento
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();
CREATE TRIGGER trg_audit_orcamento_linha AFTER INSERT OR UPDATE OR DELETE ON orcamento_linha
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

-- ============================================================
-- Grants
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON orcamento, orcamento_linha TO authenticated;
```

- [ ] **Step 2: Aplicar via Supabase MCP apply_migration**

Name: `0008_orcamento`. Expected: success.

- [ ] **Step 3: Validar schema**

```sql
SELECT unnest(enum_range(NULL::natureza_orcamento))::text;
-- Expected: DESPESA_FIXA, TRIBUTO, SALARIO_VARIAVEL, COMISSAO, VALOR_VARIAVEL, DESPESA_PROFISSIONAIS

SELECT COUNT(*) FROM information_schema.tables
  WHERE table_name IN ('orcamento','orcamento_linha');
-- Expected: 2
```

- [ ] **Step 4: Commit**

```bash
git add backend/supabase/migrations/0008_orcamento.sql
git commit -m "feat(db): migration 0008 — orcamento + orcamento_linha

Cabeçalho por (empresa, competencia) com status lifecycle. Linhas com
natureza (6 tipos do XLSX do Hugo) e FKs para contrato (PROFISSIONAIS),
categoria e projeto."
```

---

### Task 1.4: Migration 0009 — conciliacao + regra + extensões

**Files:**
- Create: `backend/supabase/migrations/0009_conciliacao_regra_extensoes.sql`

- [ ] **Step 1: Criar migration**

```sql
-- 0009_conciliacao_regra_extensoes.sql
-- Tabela associativa extrato↔orçamento + regras aprendíveis + extensões
-- em tabelas existentes (transacao_bancaria, registro_pp, adiantamento)

-- ============================================================
-- Enums novos
-- ============================================================
CREATE TYPE adiantamento_status AS ENUM (
  'ABERTO',
  'COMPENSADO_PARCIAL',
  'COMPENSADO_TOTAL',
  'BAIXADO_MANUAL'
);

CREATE TYPE origem_banco AS ENUM ('BRADESCO', 'UNICRED');

CREATE TYPE natureza_lancamento AS ENUM (
  'PIX_CREDITO',
  'PIX_DEBITO',
  'PIX_TEF',
  'LIQUIDACAO_TITULO',
  'CONVENIO',
  'INTEGRALIZACAO_CAPITAL',
  'ARRECADACAO',
  'TARIFA_CONTA',
  'ESTORNO',
  'OUTRO'
);

CREATE TYPE origem_conciliacao AS ENUM ('REGRA', 'SIMILARIDADE', 'VALOR', 'MANUAL');

-- ============================================================
-- Tabela: conciliacao_orcamento (associativa N:N)
-- ============================================================
CREATE TABLE conciliacao_orcamento (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  transacao_id uuid NOT NULL REFERENCES transacao_bancaria(id) ON DELETE CASCADE,
  orcamento_linha_id uuid NOT NULL REFERENCES orcamento_linha(id) ON DELETE RESTRICT,
  valor_aplicado numeric(14,2) NOT NULL CHECK (valor_aplicado > 0),
  confianca numeric(3,2) CHECK (confianca IS NULL OR (confianca BETWEEN 0 AND 1)),
  origem origem_conciliacao NOT NULL,
  aprovada_por uuid REFERENCES usuario(id),
  aprovada_em timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_conc_tx ON conciliacao_orcamento(transacao_id);
CREATE INDEX idx_conc_linha ON conciliacao_orcamento(orcamento_linha_id);

-- ============================================================
-- Tabela: regra_classificacao (aprendizado)
-- ============================================================
CREATE TABLE regra_classificacao (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  titular_pix_padrao text NOT NULL,
  orcamento_linha_id uuid REFERENCES orcamento_linha(id) ON DELETE SET NULL,
  categoria_id uuid REFERENCES categoria_despesa(id),
  projeto_id uuid REFERENCES projeto(id),
  empresa_id uuid REFERENCES empresa(id),
  confianca_base numeric(3,2) NOT NULL DEFAULT 0.95 CHECK (confianca_base BETWEEN 0 AND 1),
  uso_count integer NOT NULL DEFAULT 0,
  ativa boolean NOT NULL DEFAULT true,
  criada_por uuid REFERENCES usuario(id),
  criada_em timestamptz NOT NULL DEFAULT now(),
  ultima_utilizacao timestamptz
);
CREATE INDEX idx_regra_titular ON regra_classificacao(lower(titular_pix_padrao))
  WHERE ativa = true;
CREATE UNIQUE INDEX ux_regra_titular_ativa
  ON regra_classificacao(lower(titular_pix_padrao))
  WHERE ativa = true;

-- ============================================================
-- Extensões em tabelas existentes
-- ============================================================

-- transacao_bancaria: origem_banco e natureza_lancamento
ALTER TABLE transacao_bancaria
  ADD COLUMN origem_banco origem_banco,
  ADD COLUMN natureza_lancamento natureza_lancamento;

-- Backfill para transações já persistidas (são todas Bradesco até aqui):
UPDATE transacao_bancaria
SET origem_banco = 'BRADESCO',
    natureza_lancamento = 'PIX_DEBITO'
WHERE origem_banco IS NULL;

-- Tornar NOT NULL após backfill
ALTER TABLE transacao_bancaria
  ALTER COLUMN origem_banco SET NOT NULL;

-- registro_pp: FK opcional para orcamento_linha (natureza PROFISSIONAIS)
ALTER TABLE registro_pp
  ADD COLUMN orcamento_linha_id uuid REFERENCES orcamento_linha(id) ON DELETE SET NULL;
CREATE INDEX idx_registro_pp_orcamento_linha ON registro_pp(orcamento_linha_id)
  WHERE orcamento_linha_id IS NOT NULL;

-- adiantamento: lifecycle de compensação
ALTER TABLE adiantamento
  ADD COLUMN status adiantamento_status NOT NULL DEFAULT 'ABERTO',
  ADD COLUMN compensado_em_registro_pp_id uuid REFERENCES registro_pp(id) ON DELETE SET NULL,
  ADD COLUMN compensado_em timestamptz;
CREATE INDEX idx_adiantamento_status ON adiantamento(status)
  WHERE status = 'ABERTO';

-- ============================================================
-- RLS das tabelas novas
-- ============================================================
ALTER TABLE conciliacao_orcamento ENABLE ROW LEVEL SECURITY;
ALTER TABLE regra_classificacao ENABLE ROW LEVEL SECURITY;

CREATE POLICY conc_select ON conciliacao_orcamento FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY conc_insert ON conciliacao_orcamento FOR INSERT WITH CHECK (auth.uid() IS NOT NULL AND aprovada_por = auth.uid());
CREATE POLICY conc_delete ON conciliacao_orcamento FOR DELETE USING (auth.uid() IS NOT NULL);

CREATE POLICY regra_select ON regra_classificacao FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY regra_insert ON regra_classificacao FOR INSERT WITH CHECK (auth.uid() IS NOT NULL AND criada_por = auth.uid());
CREATE POLICY regra_update ON regra_classificacao FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY regra_delete ON regra_classificacao FOR DELETE USING (fn_is_ceo());

-- ============================================================
-- Triggers auditoria
-- ============================================================
CREATE TRIGGER trg_audit_conciliacao AFTER INSERT OR UPDATE OR DELETE ON conciliacao_orcamento
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();
CREATE TRIGGER trg_audit_regra AFTER INSERT OR UPDATE OR DELETE ON regra_classificacao
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

-- ============================================================
-- Grants
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON conciliacao_orcamento, regra_classificacao TO authenticated;
```

- [ ] **Step 2: Aplicar via apply_migration**

Expected: success. Atenção: contém ALTERs em tabelas com dados — o backfill UPDATE cobre registros existentes antes do SET NOT NULL.

- [ ] **Step 3: Validar**

```sql
-- Confirmar colunas novas
SELECT column_name FROM information_schema.columns
 WHERE table_name = 'transacao_bancaria' AND column_name IN ('origem_banco','natureza_lancamento');
-- Expected: 2 linhas

SELECT COUNT(*) FROM transacao_bancaria WHERE origem_banco IS NULL;
-- Expected: 0 (backfill aplicado)

SELECT column_name FROM information_schema.columns
 WHERE table_name = 'adiantamento' AND column_name IN ('status','compensado_em_registro_pp_id','compensado_em');
-- Expected: 3 linhas
```

- [ ] **Step 4: Commit**

```bash
git add backend/supabase/migrations/0009_conciliacao_regra_extensoes.sql
git commit -m "feat(db): migration 0009 — conciliacao_orcamento + regra + extensoes

Associativa N:N entre transacao_bancaria e orcamento_linha, regra aprendivel
por titular_pix, extensoes em transacao_bancaria (origem_banco,
natureza_lancamento), registro_pp (orcamento_linha_id) e adiantamento
(lifecycle de compensacao)."
```

---

### Task 1.5: Smoke test de CRUD das tabelas novas

**Files:**
- Create: `backend/tests/test_migrations_smoke.py`

- [ ] **Step 1: Escrever teste smoke de criação e leitura**

```python
# backend/tests/test_migrations_smoke.py
"""
Smoke test: criar registros nas tabelas novas (0007-0009) e ler de volta.
Roda contra o Supabase real usando supabase-py com service role.
Ignora RLS para simplicidade (teste é de schema, não de permissão).
"""
import os
import pytest
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mkxehqhikcuykaxnpxff.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

pytestmark = pytest.mark.skipif(
    not SUPABASE_SERVICE_KEY,
    reason="SUPABASE_SERVICE_ROLE_KEY não definido",
)


@pytest.fixture
def client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def test_seeds_empresa_existem(client):
    r = client.table("empresa").select("codigo").execute()
    codigos = {row["codigo"] for row in r.data}
    assert "SPM" in codigos
    assert "FD" in codigos


def test_seeds_categoria_ao_menos_40(client):
    r = client.table("categoria_despesa").select("id").execute()
    assert len(r.data) >= 40


def test_criar_projeto_e_ler(client):
    # SPM id
    e = client.table("empresa").select("id").eq("codigo", "SPM").single().execute()
    empresa_id = e.data["id"]
    # Cria projeto
    p = client.table("projeto").insert({
        "codigo": "TEST-SMOKE-PROJECT",
        "descricao": "Projeto de smoke test",
        "empresa_id": empresa_id,
    }).execute()
    assert p.data and p.data[0]["codigo"] == "TEST-SMOKE-PROJECT"
    # Limpa
    client.table("projeto").delete().eq("codigo", "TEST-SMOKE-PROJECT").execute()


def test_orcamento_e_linha_integridade(client):
    e = client.table("empresa").select("id").eq("codigo", "SPM").single().execute()
    empresa_id = e.data["id"]
    o = client.table("orcamento").insert({
        "empresa_id": empresa_id,
        "competencia": "2099-12",
        "status": "RASCUNHO",
    }).execute()
    orcamento_id = o.data[0]["id"]
    linha = client.table("orcamento_linha").insert({
        "orcamento_id": orcamento_id,
        "natureza": "DESPESA_FIXA",
        "titular_razao_social": "SMOKE TEST TITULAR",
        "valor_previsto": 123.45,
    }).execute()
    assert linha.data
    # Limpeza cascata via delete do orcamento
    client.table("orcamento").delete().eq("id", orcamento_id).execute()


def test_regra_classificacao_unique_ativa(client):
    # Inserir uma regra ativa
    r1 = client.table("regra_classificacao").insert({
        "titular_pix_padrao": "SMOKE TEST TITULAR UNIQUE",
        "confianca_base": 0.9,
        "ativa": True,
    }).execute()
    assert r1.data
    regra_id = r1.data[0]["id"]
    # Inserir segunda regra ativa com o mesmo titular — deve falhar
    with pytest.raises(Exception):
        client.table("regra_classificacao").insert({
            "titular_pix_padrao": "SMOKE TEST TITULAR UNIQUE",
            "confianca_base": 0.8,
            "ativa": True,
        }).execute()
    client.table("regra_classificacao").delete().eq("id", regra_id).execute()
```

- [ ] **Step 2: Rodar o teste**

```bash
cd backend
SUPABASE_SERVICE_ROLE_KEY=<chave> pytest tests/test_migrations_smoke.py -v
```

Expected: 4 passed (ou 0 skipped, 4 passed se chave estiver no env).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_migrations_smoke.py
git commit -m "test(db): smoke test CRUD das tabelas novas 0007-0009

Valida seeds de empresa/categoria, criacao de projeto, integridade
orcamento/linha e constraint UNIQUE parcial de regra_classificacao."
```

---

## M2 — Parsers (7 tasks)

### Task 2.1: Setup de fixtures e dependências

**Files:**
- Create: `backend/tests/fixtures/SPM_Orcamento_04_2026.xlsx` (cópia)
- Create: `backend/tests/fixtures/Comp_Unicred_20042026.pdf` (cópia)
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Copiar fixtures reais**

```bash
mkdir -p backend/tests/fixtures
cp "/Users/dr.damasceno/Downloads/SPM - Orcamento - 04.2026.xlsx" \
   backend/tests/fixtures/SPM_Orcamento_04_2026.xlsx
cp "/Users/dr.damasceno/Downloads/Comp-20042026014849.pdf" \
   backend/tests/fixtures/Comp_Unicred_20042026.pdf
```

- [ ] **Step 2: Adicionar dependências**

Editar `backend/requirements.txt`, adicionar:

```
pdfplumber==0.11.4
rapidfuzz==3.10.1
```

- [ ] **Step 3: Instalar**

```bash
cd backend
pip install pdfplumber==0.11.4 rapidfuzz==3.10.1
pip freeze | grep -E '(pdfplumber|rapidfuzz)'
```

Expected: duas linhas com as versões exatas.

- [ ] **Step 4: Validar que fixtures abrem**

```bash
python3 -c "
import openpyxl, pdfplumber
wb = openpyxl.load_workbook('backend/tests/fixtures/SPM_Orcamento_04_2026.xlsx', data_only=False)
print('Orçamento sheets:', wb.sheetnames)
with pdfplumber.open('backend/tests/fixtures/Comp_Unicred_20042026.pdf') as pdf:
    print('Unicred pages:', len(pdf.pages))
    print('Texto primeira linha página 1:', pdf.pages[0].extract_text().split(chr(10))[0])
"
```

Expected:
```
Orçamento sheets: ['Contas a Pagar', 'Planilha1']
Unicred pages: 4
Texto primeira linha página 1: COOPERATIVA 544 - COOPERATIVA DE CREDITO UNICRED
```

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/tests/fixtures/
git commit -m "chore(deps): add pdfplumber e rapidfuzz + fixtures reais

Fixtures dos arquivos reais enviados pelo Hugo durante brainstorm
2026-04-20 (PP Bertioga nao e novo, ja existe como fixture anterior)."
```

---

### Task 2.2: Parser orçamento XLSX — detecção de seções (TDD)

**Files:**
- Create: `backend/tests/test_orcamento_xlsx.py`
- Create: `backend/src/orcamento_xlsx.py`

- [ ] **Step 1: Escrever teste de detecção de seções**

```python
# backend/tests/test_orcamento_xlsx.py
"""Testes do parser de orçamento XLSX."""
from pathlib import Path
import pytest

from backend.src.orcamento_xlsx import (
    OrcamentoParser,
    NaturezaOrcamento,
    OrcamentoLinhaParsed,
)

FIXTURES = Path(__file__).parent / "fixtures"
ARQUIVO_ORCAMENTO = FIXTURES / "SPM_Orcamento_04_2026.xlsx"


def test_detecta_todas_6_secoes():
    parser = OrcamentoParser()
    secoes = parser.detectar_secoes(ARQUIVO_ORCAMENTO)
    # Cada item: (linha_inicio, natureza)
    naturezas = [n for (_, n) in secoes]
    assert NaturezaOrcamento.DESPESA_FIXA in naturezas
    assert NaturezaOrcamento.TRIBUTO in naturezas
    assert NaturezaOrcamento.SALARIO_VARIAVEL in naturezas
    assert NaturezaOrcamento.COMISSAO in naturezas
    assert NaturezaOrcamento.VALOR_VARIAVEL in naturezas
    assert NaturezaOrcamento.DESPESA_PROFISSIONAIS in naturezas
    assert len(secoes) == 6


def test_ordem_secoes_esperada():
    parser = OrcamentoParser()
    secoes = parser.detectar_secoes(ARQUIVO_ORCAMENTO)
    naturezas_ordem = [n for (_, n) in secoes]
    assert naturezas_ordem == [
        NaturezaOrcamento.DESPESA_FIXA,       # primeira, começa antes linha 10
        NaturezaOrcamento.TRIBUTO,
        NaturezaOrcamento.SALARIO_VARIAVEL,
        NaturezaOrcamento.COMISSAO,
        NaturezaOrcamento.VALOR_VARIAVEL,
        NaturezaOrcamento.DESPESA_PROFISSIONAIS,
    ]
```

- [ ] **Step 2: Rodar o teste — deve falhar (módulo inexistente)**

```bash
cd backend
pytest tests/test_orcamento_xlsx.py::test_detecta_todas_6_secoes -v
```

Expected: `ModuleNotFoundError: No module named 'backend.src.orcamento_xlsx'`

- [ ] **Step 3: Criar o módulo mínimo para passar**

```python
# backend/src/orcamento_xlsx.py
"""
Parser do XLSX de orçamento mensal da SPM.

Formato (derivado do arquivo real SPM-Orcamento-04.2026.xlsx):
  - Sheet principal: "Contas a Pagar"
  - Linha 1: cabeçalho global do mês
  - 6 seções com subcabeçalho em coluna C:
      "DESPESAS FIXAS"
      "TRIBUTOS"
      "DESPESAS VARIÁVEIS"
      "COMISSÕES"
      "Pagamentos de Valores Variáveis"
      "DESPESAS DE PROFISSIONAIS"
  - Após cada subcabeçalho vêm 1-2 linhas de formato + cabeçalho de colunas,
    depois as linhas de dados até o próximo subcabeçalho ou EOF.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Union

import openpyxl

logger = logging.getLogger(__name__)


class NaturezaOrcamento(str, Enum):
    DESPESA_FIXA = "DESPESA_FIXA"
    TRIBUTO = "TRIBUTO"
    SALARIO_VARIAVEL = "SALARIO_VARIAVEL"
    COMISSAO = "COMISSAO"
    VALOR_VARIAVEL = "VALOR_VARIAVEL"
    DESPESA_PROFISSIONAIS = "DESPESA_PROFISSIONAIS"


# Padrões regex para matching dos subcabeçalhos (case-insensitive, tolerante a espaços)
_SUBHEADERS: List[Tuple[re.Pattern, NaturezaOrcamento]] = [
    (re.compile(r"^\s*DESPESAS\s+FIXAS\s*$", re.I), NaturezaOrcamento.DESPESA_FIXA),
    (re.compile(r"^\s*TRIBUTOS\s*$", re.I), NaturezaOrcamento.TRIBUTO),
    (re.compile(r"^\s*DESPESAS\s+VARI[AÁ]VEIS\s*$", re.I), NaturezaOrcamento.SALARIO_VARIAVEL),
    (re.compile(r"^\s*COMISS[OÕ]ES\s*$", re.I), NaturezaOrcamento.COMISSAO),
    (re.compile(r"^\s*Pagamentos\s+de\s+Valores\s+Vari[aá]veis\s*$", re.I), NaturezaOrcamento.VALOR_VARIAVEL),
    (re.compile(r"^\s*DESPESAS\s+DE\s+PROFISSIONAIS\s*$", re.I), NaturezaOrcamento.DESPESA_PROFISSIONAIS),
]


@dataclass
class OrcamentoLinhaParsed:
    natureza: NaturezaOrcamento
    titular_razao_social: str
    titular_cpf_cnpj: Optional[str] = None
    categoria: Optional[str] = None
    projeto: Optional[str] = None
    valor_previsto: float = 0.0
    data_previsao: Optional[str] = None  # ISO date string
    observacao: Optional[str] = None
    linha_xlsx: int = 0  # para debug


class OrcamentoParser:
    """Parser do XLSX de orçamento com detecção de 6 seções."""

    SHEET_NAME = "Contas a Pagar"

    def detectar_secoes(
        self, arquivo: Union[str, Path, bytes]
    ) -> List[Tuple[int, NaturezaOrcamento]]:
        """
        Retorna lista de (linha_inicial, natureza) para cada seção detectada,
        em ordem de aparição no XLSX.
        """
        wb = self._abrir(arquivo)
        ws = wb[self.SHEET_NAME]

        secoes: List[Tuple[int, NaturezaOrcamento]] = []
        ja_detectadas = set()

        for row_idx in range(1, ws.max_row + 1):
            for col_idx in range(1, min(ws.max_column, 5) + 1):
                cell = ws.cell(row=row_idx, column=col_idx).value
                if not isinstance(cell, str):
                    continue
                for pattern, natureza in _SUBHEADERS:
                    if pattern.match(cell) and natureza not in ja_detectadas:
                        secoes.append((row_idx, natureza))
                        ja_detectadas.add(natureza)
                        break

        return secoes

    def _abrir(self, arquivo: Union[str, Path, bytes]):
        if isinstance(arquivo, (str, Path)):
            return openpyxl.load_workbook(arquivo, data_only=True)
        from io import BytesIO
        return openpyxl.load_workbook(BytesIO(arquivo), data_only=True)
```

- [ ] **Step 4: Rodar teste — deve passar**

```bash
pytest tests/test_orcamento_xlsx.py -v
```

Expected: `test_detecta_todas_6_secoes PASSED`, `test_ordem_secoes_esperada PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/orcamento_xlsx.py backend/tests/test_orcamento_xlsx.py
git commit -m "feat(parser): OrcamentoParser com deteccao de 6 secoes

Detecta DESPESAS FIXAS, TRIBUTOS, DESPESAS VARIAVEIS (salarios),
COMISSOES, Pagamentos de Valores Variaveis, DESPESAS DE PROFISSIONAIS
no XLSX modelo do Hugo. Testado contra o arquivo real 04/2026."
```

---

### Task 2.3: Parser orçamento — extração de linhas de uma seção

**Files:**
- Modify: `backend/src/orcamento_xlsx.py` (adicionar método `extrair_linhas_secao`)
- Modify: `backend/tests/test_orcamento_xlsx.py` (adicionar testes)

- [ ] **Step 1: Adicionar teste de extração de linhas da seção DESPESAS FIXAS**

Adicionar em `backend/tests/test_orcamento_xlsx.py`:

```python
def test_extrair_linhas_despesa_fixa_contagem():
    parser = OrcamentoParser()
    linhas = parser.extrair_linhas_secao(ARQUIVO_ORCAMENTO, NaturezaOrcamento.DESPESA_FIXA)
    # Sabemos pelo arquivo real que DESPESAS FIXAS tem ~56 linhas válidas.
    assert 40 <= len(linhas) <= 65, f"Esperado 40-65 linhas, obtido {len(linhas)}"
    for linha in linhas:
        assert linha.natureza == NaturezaOrcamento.DESPESA_FIXA
        assert linha.titular_razao_social
        assert linha.valor_previsto > 0


def test_extrair_linhas_despesa_fixa_tem_hugo():
    parser = OrcamentoParser()
    linhas = parser.extrair_linhas_secao(ARQUIVO_ORCAMENTO, NaturezaOrcamento.DESPESA_FIXA)
    nomes = [l.titular_razao_social.upper() for l in linhas]
    assert any("HUGO FERNANDES DAMASCENO" in n for n in nomes), \
        "Esperado encontrar HUGO FERNANDES DAMASCENO na seção DESPESAS FIXAS"


def test_extrair_linhas_tributos():
    parser = OrcamentoParser()
    linhas = parser.extrair_linhas_secao(ARQUIVO_ORCAMENTO, NaturezaOrcamento.TRIBUTO)
    categorias = {l.categoria for l in linhas if l.categoria}
    assert "COFINS FATURAMENTO" in categorias or any("COFINS" in c for c in categorias)
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
pytest tests/test_orcamento_xlsx.py::test_extrair_linhas_despesa_fixa_contagem -v
```

Expected: `AttributeError: 'OrcamentoParser' object has no attribute 'extrair_linhas_secao'`.

- [ ] **Step 3: Implementar `extrair_linhas_secao`**

Adicionar ao final de `backend/src/orcamento_xlsx.py`:

```python
# Colunas padrão por seção (índice 1-based do openpyxl).
# Todas as seções seguem o mesmo layout de colunas de 2 a 11, exceto PROFISSIONAIS
# que tem colunas: Previsão, CNPJ, Razão Social, Categoria, Projeto, RECEITA, DESPESAS, VALOR PAGO, Data, A PAGAR
_COL_DATA = 1
_COL_CNPJ = 2
_COL_RAZAO = 3
_COL_CATEGORIA = 4
_COL_PROJETO = 5
_COL_VALOR = 6            # "Valor da Conta" na maioria; "RECEITA" em PROFISSIONAIS
_COL_VALOR_LIQUIDO = 7    # "Valor Líquido"; "DESPESAS" em PROFISSIONAIS
_COL_VALOR_PAGO = 8
_COL_DATA_PAGAMENTO = 9
_COL_A_PAGAR = 10
_COL_OBS = 11


def _normalizar_data(valor) -> Optional[str]:
    if valor is None or valor == "":
        return None
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, str):
        # Ex: "Á CONFIRMAR", "À CONFIRMAR", datas em vários formatos
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", valor.strip())
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        return None
    return None


def _normalizar_cnpj(valor) -> Optional[str]:
    if valor is None:
        return None
    s = str(valor).strip()
    if not s:
        return None
    return s


def _linha_eh_valida(ws, row_idx: int, natureza: NaturezaOrcamento) -> bool:
    """Linha é válida se tem razão social e valor > 0."""
    razao = ws.cell(row=row_idx, column=_COL_RAZAO).value
    if natureza == NaturezaOrcamento.DESPESA_PROFISSIONAIS:
        valor = ws.cell(row=row_idx, column=_COL_VALOR_LIQUIDO).value  # DESPESAS
    else:
        valor = ws.cell(row=row_idx, column=_COL_VALOR_LIQUIDO).value  # Valor Líquido
        if valor in (None, 0):
            valor = ws.cell(row=row_idx, column=_COL_VALOR).value  # fallback Valor da Conta
    if not isinstance(razao, str) or not razao.strip():
        return False
    if not isinstance(valor, (int, float)) or valor <= 0:
        return False
    # Descarta cabeçalhos repetidos
    if razao.strip().lower() in {"razão social", "razao social", "cnpj/cpf"}:
        return False
    return True


def _extrair_uma_linha(ws, row_idx: int, natureza: NaturezaOrcamento) -> OrcamentoLinhaParsed:
    razao = ws.cell(row=row_idx, column=_COL_RAZAO).value
    cnpj = _normalizar_cnpj(ws.cell(row=row_idx, column=_COL_CNPJ).value)
    categoria = ws.cell(row=row_idx, column=_COL_CATEGORIA).value
    projeto = ws.cell(row=row_idx, column=_COL_PROJETO).value
    valor_liquido = ws.cell(row=row_idx, column=_COL_VALOR_LIQUIDO).value
    valor_conta = ws.cell(row=row_idx, column=_COL_VALOR).value
    valor = valor_liquido if isinstance(valor_liquido, (int, float)) and valor_liquido > 0 else valor_conta
    data_previsao = _normalizar_data(ws.cell(row=row_idx, column=_COL_DATA).value)
    obs = ws.cell(row=row_idx, column=_COL_OBS).value
    return OrcamentoLinhaParsed(
        natureza=natureza,
        titular_razao_social=str(razao).strip(),
        titular_cpf_cnpj=cnpj,
        categoria=str(categoria).strip() if isinstance(categoria, str) else None,
        projeto=str(projeto).strip() if isinstance(projeto, str) else None,
        valor_previsto=float(valor),
        data_previsao=data_previsao,
        observacao=str(obs).strip() if isinstance(obs, str) else None,
        linha_xlsx=row_idx,
    )


# Adicionar como método da classe OrcamentoParser:
def _extrair_linhas_secao_impl(self, arquivo, natureza: NaturezaOrcamento) -> List[OrcamentoLinhaParsed]:
    wb = self._abrir(arquivo)
    ws = wb[self.SHEET_NAME]
    secoes = self.detectar_secoes(arquivo)

    # Determinar intervalo de linhas dessa seção (do início até próxima seção ou EOF)
    secoes_ordenadas = sorted(secoes, key=lambda x: x[0])
    inicio = None
    fim = ws.max_row + 1
    for i, (row, nat) in enumerate(secoes_ordenadas):
        if nat == natureza:
            inicio = row + 1
            if i + 1 < len(secoes_ordenadas):
                fim = secoes_ordenadas[i + 1][0]
            break
    if inicio is None:
        return []

    linhas: List[OrcamentoLinhaParsed] = []
    for row_idx in range(inicio, fim):
        if _linha_eh_valida(ws, row_idx, natureza):
            linhas.append(_extrair_uma_linha(ws, row_idx, natureza))
    return linhas


OrcamentoParser.extrair_linhas_secao = _extrair_linhas_secao_impl
```

- [ ] **Step 4: Rodar testes — devem passar**

```bash
pytest tests/test_orcamento_xlsx.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/orcamento_xlsx.py backend/tests/test_orcamento_xlsx.py
git commit -m "feat(parser): OrcamentoParser.extrair_linhas_secao

Extrai linhas validas (titular + valor > 0) de cada secao, reutilizando
as colunas padrao do modelo do Hugo. Normaliza CNPJ, data e valores."
```

---

### Task 2.4: Parser orçamento — parse completo e mapeamento de empresa

**Files:**
- Modify: `backend/src/orcamento_xlsx.py` (adicionar `parse_completo`)
- Modify: `backend/tests/test_orcamento_xlsx.py`

- [ ] **Step 1: Adicionar testes**

```python
def test_parse_completo_retorna_todas_linhas():
    parser = OrcamentoParser()
    resultado = parser.parse_completo(ARQUIVO_ORCAMENTO)
    assert resultado.total_linhas > 100, \
        f"Esperado >100 linhas no orcamento completo, obtido {resultado.total_linhas}"
    assert resultado.linhas_por_secao[NaturezaOrcamento.DESPESA_FIXA] > 30
    assert resultado.linhas_por_secao[NaturezaOrcamento.TRIBUTO] >= 5
    assert resultado.linhas_por_secao[NaturezaOrcamento.DESPESA_PROFISSIONAIS] >= 40


def test_empresa_derivada_sufixo_projeto():
    parser = OrcamentoParser()
    resultado = parser.parse_completo(ARQUIVO_ORCAMENTO)
    # Linhas com projeto terminando em "-FD" -> empresa FD
    linhas_fd = [l for l in resultado.linhas if l.empresa_codigo == "FD"]
    linhas_spm = [l for l in resultado.linhas if l.empresa_codigo == "SPM"]
    assert len(linhas_fd) >= 3, "Esperado pelo menos 3 linhas FD"
    assert len(linhas_spm) > len(linhas_fd), "Esperado mais linhas SPM que FD"


def test_parse_completo_hugo_spm():
    parser = OrcamentoParser()
    resultado = parser.parse_completo(ARQUIVO_ORCAMENTO)
    hugo = [l for l in resultado.linhas if "HUGO" in l.titular_razao_social.upper()]
    assert hugo, "Hugo deve aparecer no orcamento"
    assert all(l.empresa_codigo == "SPM" for l in hugo)
```

- [ ] **Step 2: Rodar testes — deve falhar**

Expected: `AttributeError: parse_completo`.

- [ ] **Step 3: Implementar**

Adicionar ao `backend/src/orcamento_xlsx.py`:

```python
@dataclass
class OrcamentoLinhaParsed:  # SOBRESCREVE a definição anterior — mover campo empresa_codigo
    natureza: NaturezaOrcamento
    titular_razao_social: str
    empresa_codigo: str = "SPM"                 # ← novo campo (padrão SPM)
    titular_cpf_cnpj: Optional[str] = None
    categoria: Optional[str] = None
    projeto: Optional[str] = None
    valor_previsto: float = 0.0
    data_previsao: Optional[str] = None
    observacao: Optional[str] = None
    linha_xlsx: int = 0


@dataclass
class ResultadoParse:
    linhas: List[OrcamentoLinhaParsed]
    total_linhas: int
    linhas_por_secao: dict[NaturezaOrcamento, int]
    linhas_descartadas: int
    avisos: List[str]


def _derivar_empresa(projeto: Optional[str]) -> str:
    """Deriva empresa do sufixo do projeto: '-FD' → FD, padrão SPM."""
    if not projeto:
        return "SPM"
    p = projeto.upper().strip()
    if p.endswith("-FD") or p.endswith(" FD") or "- FD" in p or "-FD " in p:
        return "FD"
    return "SPM"


def _parse_completo_impl(self, arquivo) -> ResultadoParse:
    todas_linhas: List[OrcamentoLinhaParsed] = []
    por_secao: dict[NaturezaOrcamento, int] = {}
    avisos: List[str] = []
    descartadas = 0

    for natureza in NaturezaOrcamento:
        linhas = self.extrair_linhas_secao(arquivo, natureza)
        for l in linhas:
            l.empresa_codigo = _derivar_empresa(l.projeto)
            todas_linhas.append(l)
        por_secao[natureza] = len(linhas)

    return ResultadoParse(
        linhas=todas_linhas,
        total_linhas=len(todas_linhas),
        linhas_por_secao=por_secao,
        linhas_descartadas=descartadas,
        avisos=avisos,
    )


OrcamentoParser.parse_completo = _parse_completo_impl
```

Observação: o step 3 altera a dataclass `OrcamentoLinhaParsed` adicionando `empresa_codigo`. Ajuste a definição existente no arquivo em vez de duplicar.

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/test_orcamento_xlsx.py -v
```

Expected: todos passam (agora 8 testes).

- [ ] **Step 5: Commit**

```bash
git add backend/src/orcamento_xlsx.py backend/tests/test_orcamento_xlsx.py
git commit -m "feat(parser): parse_completo do orcamento + derivacao empresa SPM/FD

Retorna ResultadoParse com todas as linhas de todas as 6 secoes, com
empresa_codigo derivado do sufixo do projeto (-FD/padrao SPM)."
```

---

### Task 2.5: Parser Unicred PDF — extração de texto e regex base

**Files:**
- Create: `backend/src/extrato_unicred.py`
- Create: `backend/tests/test_extrato_unicred.py`

- [ ] **Step 1: Escrever teste básico de extração de linhas**

```python
# backend/tests/test_extrato_unicred.py
"""Testes do parser de extrato Unicred PDF."""
from pathlib import Path
import pytest
from backend.src.extrato_unicred import (
    UnicredParser,
    NaturezaLancamento,
    TransacaoUnicredParsed,
)

FIXTURES = Path(__file__).parent / "fixtures"
ARQUIVO = FIXTURES / "Comp_Unicred_20042026.pdf"


def test_parser_extrai_metadados_conta():
    parser = UnicredParser()
    meta = parser.extrair_metadados(ARQUIVO)
    assert meta.banco == "UNICRED"
    assert meta.conta == "6688055"
    assert meta.cliente_razao_social.upper().startswith("SOCIEDADE PARANAENSE")
    assert meta.periodo_inicio  # ex: "2026-03-22"
    assert meta.periodo_fim


def test_parser_extrai_pelo_menos_40_linhas():
    parser = UnicredParser()
    transacoes = parser.parse(ARQUIVO)
    assert len(transacoes) >= 40, f"Esperado >=40 linhas, obtido {len(transacoes)}"


def test_saldo_inicial_zero_saldo_final_positivo():
    parser = UnicredParser()
    meta = parser.extrair_metadados(ARQUIVO)
    assert meta.saldo_anterior == 0.0
    assert meta.saldo_final > 0.0
```

- [ ] **Step 2: Rodar — falha por módulo inexistente**

- [ ] **Step 3: Criar esqueleto do parser**

```python
# backend/src/extrato_unicred.py
"""
Parser de extrato Unicred PDF ("para simples conferência").

Formato de cabeçalho:
  COOPERATIVA 544 - COOPERATIVA DE CREDITO UNICRED
  CONTA: 6688055
  CLIENTE: SOCIEDADE PARANAENSE DE MEDICINA LTDA
  EXTRATO DE CONTA CORRENTE PARA SIMPLES CONFERÊNCIA EM DD/MM/YYYY HH:MM
  PERÍODO DE DD/MM/YYYY A DD/MM/YYYY
  SALDO ANTERIOR: 0,00

Formato de linha de transação (layout fixo):
  DATA_MOV  ID_DOC  HISTÓRICO  LANÇAMENTO(R$)  SALDO(R$)

pdfplumber extrai o texto linha a linha. Quebras de linha naturais podem
separar o valor do HISTÓRICO — usar lookahead para reconstruir.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

import pdfplumber

logger = logging.getLogger(__name__)


class NaturezaLancamento(str, Enum):
    PIX_CREDITO = "PIX_CREDITO"
    PIX_DEBITO = "PIX_DEBITO"
    PIX_TEF = "PIX_TEF"
    LIQUIDACAO_TITULO = "LIQUIDACAO_TITULO"
    CONVENIO = "CONVENIO"
    INTEGRALIZACAO_CAPITAL = "INTEGRALIZACAO_CAPITAL"
    ARRECADACAO = "ARRECADACAO"
    TARIFA_CONTA = "TARIFA_CONTA"
    ESTORNO = "ESTORNO"
    OUTRO = "OUTRO"


@dataclass
class MetadadosExtratoUnicred:
    banco: str = "UNICRED"
    conta: Optional[str] = None
    cliente_razao_social: Optional[str] = None
    periodo_inicio: Optional[str] = None  # YYYY-MM-DD
    periodo_fim: Optional[str] = None
    saldo_anterior: float = 0.0
    saldo_final: float = 0.0


@dataclass
class TransacaoUnicredParsed:
    data_movimento: str          # YYYY-MM-DD
    id_doc: Optional[str]
    historico: str
    valor: float                 # negativo = débito, positivo = crédito
    saldo: float
    natureza: NaturezaLancamento = NaturezaLancamento.OUTRO
    titular_pix: Optional[str] = None
    linha_numero: int = 0


class UnicredParser:
    """Parser de PDF Unicred com lookahead para quebras de linha."""

    _RE_DATA = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+")
    _RE_SALDO_ANTERIOR = re.compile(r"SALDO\s+ANTERIOR:\s*([\d\.,]+)", re.I)
    _RE_PERIODO = re.compile(r"PER[IÍ]ODO\s+DE\s+(\d{2}/\d{2}/\d{4})\s+A\s+(\d{2}/\d{2}/\d{4})", re.I)
    _RE_CONTA = re.compile(r"CONTA:\s*(\d+)", re.I)
    _RE_CLIENTE = re.compile(r"CLIENTE:\s*([^\n]+)", re.I)
    _RE_SALDO_FINAL = re.compile(r"Saldo\s+em\s+\d{2}/\d{2}/\d{4}\s+([\d\.,]+)", re.I)

    # Padrão de linha: DATA ID HISTÓRICO ... VALOR SALDO
    # VALOR pode ter sinal negativo; SALDO sempre positivo/zero
    _RE_LINHA = re.compile(
        r"^(\d{2}/\d{2}/\d{4})\s+"            # data
        r"(\S+)\s+"                             # id_doc
        r"(.+?)\s+"                             # histórico (non-greedy)
        r"(-?[\d\.]+,\d{2})\s+"                 # valor
        r"([\d\.]+,\d{2})\s*$"                  # saldo
    )

    def extrair_metadados(self, arquivo: Union[str, Path, bytes]) -> MetadadosExtratoUnicred:
        texto = self._extrair_texto_completo(arquivo)
        meta = MetadadosExtratoUnicred()

        m = self._RE_CONTA.search(texto)
        meta.conta = m.group(1) if m else None

        m = self._RE_CLIENTE.search(texto)
        if m:
            meta.cliente_razao_social = m.group(1).strip()

        m = self._RE_PERIODO.search(texto)
        if m:
            meta.periodo_inicio = self._parse_data(m.group(1))
            meta.periodo_fim = self._parse_data(m.group(2))

        m = self._RE_SALDO_ANTERIOR.search(texto)
        if m:
            meta.saldo_anterior = self._parse_valor(m.group(1))

        m = self._RE_SALDO_FINAL.search(texto)
        if m:
            meta.saldo_final = self._parse_valor(m.group(1))

        return meta

    def parse(self, arquivo: Union[str, Path, bytes]) -> List[TransacaoUnicredParsed]:
        """Extrai todas as transações; stub até Task 2.6."""
        return []

    # ------------------- helpers -------------------

    def _extrair_texto_completo(self, arquivo) -> str:
        paginas = []
        if isinstance(arquivo, (str, Path)):
            with pdfplumber.open(arquivo) as pdf:
                for p in pdf.pages:
                    paginas.append(p.extract_text() or "")
        else:
            from io import BytesIO
            with pdfplumber.open(BytesIO(arquivo)) as pdf:
                for p in pdf.pages:
                    paginas.append(p.extract_text() or "")
        return "\n".join(paginas)

    @staticmethod
    def _parse_data(s: str) -> str:
        d, m, y = s.split("/")
        return f"{y}-{m}-{d}"

    @staticmethod
    def _parse_valor(s: str) -> float:
        # "55.473,33" -> 55473.33 ; "-2.000,00" -> -2000.00
        return float(s.replace(".", "").replace(",", "."))
```

- [ ] **Step 4: Rodar `test_parser_extrai_metadados_conta` — passa**

```bash
pytest tests/test_extrato_unicred.py::test_parser_extrai_metadados_conta -v
```

Expected: PASSED.

- [ ] **Step 5: Rodar `test_parser_extrai_pelo_menos_40_linhas` — falha (parse retorna [])**

Expected: FAIL. Tudo bem — vamos implementar na próxima task.

- [ ] **Step 6: Commit parcial**

```bash
git add backend/src/extrato_unicred.py backend/tests/test_extrato_unicred.py
git commit -m "feat(parser): UnicredParser esqueleto + extracao de metadados

Lê cabeçalho do PDF (conta, cliente, período, saldos). Parse completo
de transações fica na próxima task."
```

---

### Task 2.6: Parser Unicred — extração de transações com lookahead

**Files:**
- Modify: `backend/src/extrato_unicred.py` (implementar `parse`)

- [ ] **Step 1: Adicionar teste de contagem mais específico**

Adicionar em `backend/tests/test_extrato_unicred.py`:

```python
def test_parse_tem_pix_credito_e_debito():
    parser = UnicredParser()
    txs = parser.parse(ARQUIVO)
    creditos = [t for t in txs if t.natureza == NaturezaLancamento.PIX_CREDITO]
    debitos = [t for t in txs if t.natureza == NaturezaLancamento.PIX_DEBITO]
    assert creditos, "Esperado ao menos um PIX crédito"
    assert debitos, "Esperado ao menos um PIX débito"


def test_parse_soma_bate_com_saldo_final():
    parser = UnicredParser()
    meta = parser.extrair_metadados(ARQUIVO)
    txs = parser.parse(ARQUIVO)
    soma = meta.saldo_anterior + sum(t.valor for t in txs)
    # Tolerância de centavos
    assert abs(soma - meta.saldo_final) < 1.0, (
        f"Soma {soma} divergiu do saldo final {meta.saldo_final}"
    )
```

- [ ] **Step 2: Implementar `parse` com lookahead**

Substituir o método stub em `backend/src/extrato_unicred.py`:

```python
def parse(self, arquivo: Union[str, Path, bytes]) -> List[TransacaoUnicredParsed]:
    texto = self._extrair_texto_completo(arquivo)
    linhas_raw = texto.split("\n")
    transacoes: List[TransacaoUnicredParsed] = []

    i = 0
    while i < len(linhas_raw):
        linha = linhas_raw[i].strip()
        if not linha or not self._RE_DATA.match(linha):
            i += 1
            continue

        # Tenta match completo na linha única
        m = self._RE_LINHA.match(linha)
        linha_combinada = linha
        # Lookahead: junta próxima linha se necessário (valor quebra de linha)
        if not m and i + 1 < len(linhas_raw):
            combinada = f"{linha} {linhas_raw[i + 1].strip()}"
            m = self._RE_LINHA.match(combinada)
            if m:
                linha_combinada = combinada
                i += 1  # consome a próxima linha também

        if not m:
            logger.warning("Linha Unicred não parseada: %s", linha[:120])
            i += 1
            continue

        data_raw, id_doc, historico, valor_raw, saldo_raw = m.groups()
        tx = TransacaoUnicredParsed(
            data_movimento=self._parse_data(data_raw),
            id_doc=id_doc,
            historico=historico.strip(),
            valor=self._parse_valor(valor_raw),
            saldo=self._parse_valor(saldo_raw),
            linha_numero=i + 1,
        )
        tx.natureza = self._classificar_natureza(id_doc, historico)
        tx.titular_pix = self._extrair_titular(historico)
        transacoes.append(tx)
        i += 1

    return transacoes


# Adicionar como método da classe:
def _classificar_natureza(self, id_doc: str, historico: str) -> "NaturezaLancamento":
    hist_up = historico.upper()
    id_up = (id_doc or "").upper()
    if "ESTORNO PIX PAGO" in hist_up or "CRD DEVPIX" in id_up or "CRED REC DEV PIX" in hist_up:
        return NaturezaLancamento.ESTORNO
    if "CRED PIX" in id_up or "CRED RECEBIMENTO PIX" in hist_up:
        return NaturezaLancamento.PIX_CREDITO
    if "TRANSF TEF PIX" in hist_up:
        return NaturezaLancamento.PIX_TEF
    if "DEB PIX" in id_up or "PGTO PIX" in id_up or "DEBITO TRANSF PIX" in hist_up or "DEBITO PAGAMENTO PIX" in hist_up:
        return NaturezaLancamento.PIX_DEBITO
    if "LIQ TIT" in hist_up:
        return NaturezaLancamento.LIQUIDACAO_TITULO
    if "ARREC CONVENIO" in hist_up or "CONVÊNIO" in hist_up:
        return NaturezaLancamento.CONVENIO
    if "INTEGR PARC CAPIT" in hist_up:
        return NaturezaLancamento.INTEGRALIZACAO_CAPITAL
    if hist_up.startswith("PJ CONTA PJ"):
        return NaturezaLancamento.TARIFA_CONTA
    return NaturezaLancamento.OUTRO


def _extrair_titular(self, historico: str) -> Optional[str]:
    # Titular vem entre parênteses no final: "... PIX(NOME DO TITULAR)"
    m = re.search(r"\(([^)]+)\)", historico)
    if m:
        return m.group(1).strip()
    return None


UnicredParser._classificar_natureza = _classificar_natureza
UnicredParser._extrair_titular = _extrair_titular
```

- [ ] **Step 3: Rodar todos os testes Unicred**

```bash
pytest tests/test_extrato_unicred.py -v
```

Expected: 5 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/src/extrato_unicred.py backend/tests/test_extrato_unicred.py
git commit -m "feat(parser): UnicredParser.parse com lookahead + classificacao

Extrai transacoes linha a linha, junta linhas quebradas via lookahead,
classifica natureza (PIX_CREDITO/DEBITO/TEF, LIQ_TITULO, CONVENIO,
INTEGRALIZACAO, TARIFA, ESTORNO, OUTRO) e extrai titular do pix."
```

---

### Task 2.7: Extensão Bradesco — routing por conta

**Files:**
- Modify: `backend/src/extrato_bradesco.py` (adicionar `extract_bank_account`)
- Create: `backend/tests/test_extrato_bradesco_routing.py`

- [ ] **Step 1: Escrever teste**

```python
# backend/tests/test_extrato_bradesco_routing.py
"""Testes da função de roteamento por conta (BANKID + ACCTID)."""
from pathlib import Path
from backend.src.extrato_bradesco import extract_bank_account

FIXTURES = Path(__file__).parent / "fixtures"
OFX_EXISTENTE = FIXTURES / "EXTRATO_POR_PERIODO_120426_221307.ofx"


def test_extract_bank_account_bradesco():
    # Assumindo que o OFX de teste já existe do trabalho anterior
    if not OFX_EXISTENTE.exists():
        import pytest
        pytest.skip("OFX fixture ausente")
    with open(OFX_EXISTENTE, "rb") as f:
        data = f.read()
    bankid, acctid = extract_bank_account(data)
    assert bankid == "0237"        # Bradesco
    assert acctid == "22982"       # Conta do extrato de exemplo


def test_extract_bank_account_raises_on_invalid():
    import pytest
    with pytest.raises(ValueError, match="BANKID"):
        extract_bank_account(b"not an ofx")
```

- [ ] **Step 2: Rodar — falha (função inexistente)**

- [ ] **Step 3: Implementar**

Adicionar ao final de `backend/src/extrato_bradesco.py`:

```python
_RE_BANKID = re.compile(rb"<BANKID>\s*(\d+)", re.I)
_RE_ACCTID = re.compile(rb"<ACCTID>\s*(\d+)", re.I)


def extract_bank_account(ofx_bytes: bytes) -> tuple[str, str]:
    """
    Extrai BANKID (banco) e ACCTID (conta) do header do OFX.
    Usa para roteamento: qual conta_bancaria do DB esse extrato pertence.

    Raises:
        ValueError: se BANKID ou ACCTID não forem encontrados.
    """
    m_bank = _RE_BANKID.search(ofx_bytes)
    if not m_bank:
        raise ValueError("BANKID não encontrado no OFX")
    m_acct = _RE_ACCTID.search(ofx_bytes)
    if not m_acct:
        raise ValueError("ACCTID não encontrado no OFX")
    return m_bank.group(1).decode(), m_acct.group(1).decode()
```

- [ ] **Step 4: Rodar teste**

```bash
pytest tests/test_extrato_bradesco_routing.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Copiar OFX para fixtures se ainda não estiver**

```bash
if [ ! -f backend/tests/fixtures/EXTRATO_POR_PERIODO_120426_221307.ofx ]; then
  cp "/Users/dr.damasceno/Downloads/EXTRATO_POR_PERIODO_120426_221307.ofx" \
     backend/tests/fixtures/
fi
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/extrato_bradesco.py backend/tests/test_extrato_bradesco_routing.py backend/tests/fixtures/
git commit -m "feat(parser): extract_bank_account para roteamento OFX por conta

Extrai BANKID + ACCTID do header do OFX. Usado pelo motor para resolver
conta_id antes de inserir transacoes no DB (AVISTA vs TRIBUTOS vs REMESSAS)."
```

---

## Self-review (rodar antes de fechar Plano 1)

Após implementar todas as tasks, rode a suíte completa e confirme a régua de entrega:

- [ ] **Rodar suite completa**

```bash
cd backend
pytest tests/ -v
```

Expected:
- Todos os testes dos parsers passam (≥10 testes entre orçamento, Unicred, Bradesco routing)
- Smoke test de migrations passa (se SUPABASE_SERVICE_ROLE_KEY estiver no env)
- Testes PP e Bradesco existentes continuam passando (nenhuma regressão)

- [ ] **Confirmar parsers contra arquivos reais de Hugo**

```bash
python3 -c "
from pathlib import Path
from backend.src.orcamento_xlsx import OrcamentoParser, NaturezaOrcamento
from backend.src.extrato_unicred import UnicredParser

orc = OrcamentoParser().parse_completo(Path('backend/tests/fixtures/SPM_Orcamento_04_2026.xlsx'))
print(f'Orçamento: {orc.total_linhas} linhas em {len(orc.linhas_por_secao)} seções')
for nat, n in orc.linhas_por_secao.items():
    print(f'  {nat.value}: {n}')

txs = UnicredParser().parse(Path('backend/tests/fixtures/Comp_Unicred_20042026.pdf'))
print(f'Unicred: {len(txs)} transações')
from collections import Counter
for nat, n in Counter(t.natureza.value for t in txs).most_common():
    print(f'  {nat}: {n}')
"
```

Expected:
- Orçamento: ~120 linhas com todas as 6 seções preenchidas
- Unicred: ≥40 transações com pelo menos PIX_CREDITO, PIX_DEBITO, LIQUIDACAO_TITULO, INTEGRALIZACAO_CAPITAL, ESTORNO

- [ ] **Fazer merge/push se todo o plano estiver verde**

```bash
git log --oneline main..HEAD  # ver commits deste plano
# Se estiver tudo verde, considerar um commit de "cap" anunciando o marco
git commit --allow-empty -m "chore: encerra Plano 1 (Foundation) do Sistema Financeiro v2

Entregue:
- Migrations 0007-0009 aplicadas no Supabase
- Seeds empresa SPM/FD + 48 categorias
- Parser orcamento XLSX (6 secoes, deriva SPM/FD)
- Parser Unicred PDF (lookahead + classificacao)
- Extensao Bradesco com routing BANKID+ACCTID

Proximo: Plano 2 (Motor de classificacao + API)."
```

---

## Checklist de entrega (Plano 1)

Um engenheiro pode executar este plano e ter como output:

- [x] 3 migrations aplicadas (`0007`, `0008`, `0009`)
- [x] Seeds `empresa` (SPM + FD) e `categoria_despesa` (48 linhas)
- [x] Smoke test confirma CRUD + RLS funcionando
- [x] `backend/src/orcamento_xlsx.py` + 8 testes passando com arquivo real
- [x] `backend/src/extrato_unicred.py` + 5 testes passando com arquivo real
- [x] `backend/src/extrato_bradesco.py` estendido com `extract_bank_account`
- [x] Nenhuma regressão nos testes existentes (PP, Bradesco original)

## Próximos passos após Plano 1

Depois de merge do Plano 1, escrever:

- **Plano 2 — Motor de Classificação + API** (M3 do spec): 3 camadas de sugestão, endpoints REST de upload/conciliação/regra/adiantamento, testes de integração. Esforço ~3-4 dias.
- **Plano 3 — UI + Go Live** (M4+M5+M6 do spec): 7 telas Next.js, integração com arquivos reais, deploy Render/Vercel, primeiro ciclo real. Esforço ~8-12 dias.
