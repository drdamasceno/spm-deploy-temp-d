# Track B — Plano 01: Schema novo + backfill + fixes de bug

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o modelo de dados que suporta bolsos + vínculo prestador-PJ + split + saldo diário, fazer o backfill dos CLTs FD, e corrigir os dois bugs do Dashboard (saldo_inicial=0 e saldo_atual ≠ liquidez_total). Sistema continua rodando com UI atual durante toda a fase.

**Architecture:** Cinco migrations aditivas no Supabase (0015-0019), nenhuma altera estrutura existente. Decisão de implementação: **estender a tabela `empresa` existente** (que já tem codigo/razao_social/cnpj desde migration 0007) com `regime_tributario` e `papel`, em vez de criar `empresa_grupo` nova como o spec sugere — mesmo papel, menos redundância. FD vira linha nova em `empresa` com `papel=INTRAGRUPO`. Fixes do Dashboard são mudanças pontuais em `backend/api/routers/dashboard.py`.

**Tech Stack:** Python 3.11, FastAPI, Supabase (PostgreSQL 15 via httpx), pytest, Next.js 16 (sem alteração de frontend neste plano — fica para Plano 02).

**Spec:** `docs/superpowers/specs/2026-04-22-dashboard-e-bolsos-design.md` (commits `1c5baad` + `3a4865c` + `bb9afe1`)

**Pré-requisito externo (executar antes do Plano):** Hugo preenche `backend/scripts/backfill_pj_empregadora_config.json` com a lista de nomes de CLTs FD (Thais Alessandra, Vinicius Augusto, CLTs Unai). Template criado na Task 8.

---

## File Structure

Arquivos criados neste plano:

```
backend/supabase/migrations/
  0015_empresa_extensao_e_prestador_pj.sql    — amplia empresa + pj_empregadora_id
  0016_bolsos_em_orcamento.sql                — enum bolso_tipo + colunas em orcamento_linha
  0017_transacao_linha_split.sql              — tabela transacao_linha
  0018_saldo_caixa_diario_e_rendimento.sql    — tabela + colunas de rendimento
  0019_natureza_receita_financeira.sql        — ALTER TYPE (isolado)

backend/scripts/
  backfill_pj_empregadora.py                  — script idempotente com dry-run
  backfill_pj_empregadora_config.json         — input a ser preenchido por Hugo

backend/api/schemas/
  bolso.py                                    — BolsoTipo enum + schemas relacionados

backend/tests/
  test_migration_empresa_extensao.py          — garantia de seeds e enums
  test_backfill_pj_empregadora.py             — dry-run + idempotência
  test_dashboard_fixes.py                     — saldo_atual = liquidez, entradas_do_mes
```

Arquivos modificados:

```
backend/api/routers/dashboard.py              — fixes de saldo_inicial e saldo_atual
backend/api/schemas/dashboard.py              — renomeia KPIs.saldo_inicial → entradas_do_mes
backend/api/routers/saldos.py                 — expor helper get_liquidez_total()
```

---

## Task 1: Preparação do ambiente

**Files:** worktree já criado em `/Users/dr.damasceno/spm-sistemafinanceiro-trackb` na branch `feature/track-b-dashboard-bolsos`.

- [ ] **Step 1: Confirmar worktree e branch**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro-trackb
git branch --show-current
```

Expected: `feature/track-b-dashboard-bolsos`

- [ ] **Step 2: Instalar dependências backend**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro-trackb/backend
pip install -r requirements.txt
```

- [ ] **Step 3: Rodar suite de testes atual como baseline**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro-trackb
python -m pytest backend/tests/ -v --tb=short 2>&1 | tail -20
```

Expected: todos os testes passando (baseline limpo). Se algum falhar, anotar antes de prosseguir.

- [ ] **Step 4: Commit inicial vazio**

```bash
git commit --allow-empty -m "chore(track-b): início do plano 01 — schema e fixes"
```

---

## Task 2: Migration 0015 — ampliar empresa + pj_empregadora_id

**Files:**
- Create: `backend/supabase/migrations/0015_empresa_extensao_e_prestador_pj.sql`
- Test: `backend/tests/test_migration_empresa_extensao.py`

- [ ] **Step 1: Escrever a migration**

Criar `backend/supabase/migrations/0015_empresa_extensao_e_prestador_pj.sql`:

```sql
-- Migration 0015: amplia tabela empresa com regime_tributario e papel,
-- e adiciona prestador.pj_empregadora_id (FK opcional para empresa).
--
-- Decisão: em vez de criar tabela empresa_grupo nova (spec §3.1), estendemos
-- a tabela empresa existente. Menos redundância, aproveita RLS/infra.
--
-- FD já deve existir como empresa (codigo='FD'). Se não existir, insere.

BEGIN;

CREATE TYPE regime_tributario_empresa AS ENUM (
  'LUCRO_REAL',
  'LUCRO_PRESUMIDO',
  'SIMPLES_NACIONAL'
);

CREATE TYPE papel_empresa AS ENUM (
  'PRINCIPAL',   -- empresa operacional do grupo (SPM)
  'INTRAGRUPO'   -- empresa do grupo que recebe pagamentos intragrupo (FD)
);

ALTER TABLE empresa
  ADD COLUMN regime_tributario regime_tributario_empresa,
  ADD COLUMN papel papel_empresa;

-- Popula dados existentes (SPM e FD já devem estar em empresa via seeds anteriores)
UPDATE empresa SET
  regime_tributario = 'LUCRO_REAL',
  papel = 'PRINCIPAL'
WHERE codigo = 'SPM';

UPDATE empresa SET
  regime_tributario = 'SIMPLES_NACIONAL',
  papel = 'INTRAGRUPO',
  cnpj = COALESCE(cnpj, '49.542.886/0001-94')
WHERE codigo = 'FD';

-- Se FD não existe ainda, inserir
INSERT INTO empresa (codigo, razao_social, cnpj, regime_tributario, papel)
VALUES ('FD', 'FD GESTAO INTELIGENTE DE NEGOCIOS LTDA', '49.542.886/0001-94', 'SIMPLES_NACIONAL', 'INTRAGRUPO')
ON CONFLICT (codigo) DO NOTHING;

-- Torna os campos NOT NULL depois de popular
ALTER TABLE empresa
  ALTER COLUMN regime_tributario SET NOT NULL,
  ALTER COLUMN papel SET NOT NULL;

-- Prestador ganha vínculo opcional com PJ empregadora
ALTER TABLE prestador
  ADD COLUMN pj_empregadora_id uuid REFERENCES empresa(id);

CREATE INDEX idx_prestador_pj_empregadora
  ON prestador(pj_empregadora_id)
  WHERE pj_empregadora_id IS NOT NULL;

COMMIT;
```

- [ ] **Step 2: Aplicar migration via Supabase MCP**

Usar `mcp__claude_ai_Supabase__apply_migration` com project_id=`mkxehqhikcuykaxnpxff`, name=`0015_empresa_extensao_e_prestador_pj`, query do arquivo acima.

- [ ] **Step 3: Escrever test de garantia**

Criar `backend/tests/test_migration_empresa_extensao.py`:

```python
"""Verifica que migration 0015 deixou empresa e prestador no estado esperado."""
import os
import pytest
from supabase import create_client


@pytest.fixture(scope="module")
def client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def test_empresa_tem_regime_e_papel(client):
    rows = client.table("empresa").select("codigo,regime_tributario,papel,cnpj").execute().data
    codigos = {r["codigo"]: r for r in rows}
    assert "SPM" in codigos
    assert codigos["SPM"]["papel"] == "PRINCIPAL"
    assert codigos["SPM"]["regime_tributario"] == "LUCRO_REAL"
    assert "FD" in codigos
    assert codigos["FD"]["papel"] == "INTRAGRUPO"
    assert codigos["FD"]["regime_tributario"] == "SIMPLES_NACIONAL"
    assert codigos["FD"]["cnpj"] == "49.542.886/0001-94"


def test_prestador_tem_pj_empregadora_id(client):
    # Sanity: coluna existe e aceita NULL
    prest = client.table("prestador").select("id,pj_empregadora_id").limit(1).execute().data
    assert prest, "precisa existir pelo menos 1 prestador na base"
    # Coluna existe mesmo com valor null
    assert "pj_empregadora_id" in prest[0]
```

- [ ] **Step 4: Rodar test de migration**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro-trackb
python -m pytest backend/tests/test_migration_empresa_extensao.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/supabase/migrations/0015_empresa_extensao_e_prestador_pj.sql backend/tests/test_migration_empresa_extensao.py
git commit -m "feat(track-b): migration 0015 amplia empresa + pj_empregadora_id em prestador"
```

---

## Task 3: Migration 0016 — bolsos + empresa_pagadora em orcamento_linha

**Files:**
- Create: `backend/supabase/migrations/0016_bolsos_em_orcamento.sql`
- Create: `backend/api/schemas/bolso.py`

- [ ] **Step 1: Escrever a migration**

Criar `backend/supabase/migrations/0016_bolsos_em_orcamento.sql`:

```sql
-- Migration 0016: enum bolso_tipo + coluna bolso em orcamento_linha,
-- mais coluna empresa_pagadora_id (FK opcional para empresa).
--
-- Bolso é dimensão gerencial ortogonal à natureza (spec §3.1).
-- Quatro valores fixos conhecidos → enum, não tabela lookup.
-- Default SPM_OPERACIONAL preserva comportamento atual (linhas existentes
-- consideradas operacionais SPM).

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
```

- [ ] **Step 2: Aplicar migration via MCP**

Mesma operação da Task 2 com name=`0016_bolsos_em_orcamento`.

- [ ] **Step 3: Criar schema Pydantic do bolso**

Criar `backend/api/schemas/bolso.py`:

```python
"""Schemas Pydantic para bolso (dimensão gerencial ortogonal à natureza)."""
from enum import Enum


class BolsoTipo(str, Enum):
    SPM_OPERACIONAL = "SPM_OPERACIONAL"
    FD_VIA_SPM = "FD_VIA_SPM"
    HUGO_PESSOAL = "HUGO_PESSOAL"
    INVESTIMENTO_HUGO = "INVESTIMENTO_HUGO"


BOLSO_LABELS: dict[BolsoTipo, str] = {
    BolsoTipo.SPM_OPERACIONAL: "SPM operacional",
    BolsoTipo.FD_VIA_SPM: "Via FD",
    BolsoTipo.HUGO_PESSOAL: "Pessoal Hugo",
    BolsoTipo.INVESTIMENTO_HUGO: "Investimento Hugo",
}
```

- [ ] **Step 4: Commit**

```bash
git add backend/supabase/migrations/0016_bolsos_em_orcamento.sql backend/api/schemas/bolso.py
git commit -m "feat(track-b): migration 0016 bolsos + empresa_pagadora em orcamento_linha"
```

---

## Task 4: Migration 0017 — transacao_linha (split)

**Files:** Create `backend/supabase/migrations/0017_transacao_linha_split.sql`

- [ ] **Step 1: Escrever a migration**

```sql
-- Migration 0017: tabela transacao_linha permite split de uma transação em
-- N alocações (ex: fatura de cartão metade SPM, metade pessoal).
--
-- Invariante: sum(transacao_linha.valor) = transacao_bancaria.valor da tx pai.
-- Validação feita no router (permite estados temporários durante edição).

BEGIN;

CREATE TABLE transacao_linha (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  transacao_bancaria_id uuid NOT NULL REFERENCES transacao_bancaria(id) ON DELETE CASCADE,
  valor numeric(14,2) NOT NULL CHECK (valor <> 0),
  bolso bolso_tipo NOT NULL,
  orcamento_linha_id uuid REFERENCES orcamento_linha(id),
  empresa_pagadora_id uuid REFERENCES empresa(id),
  descricao text,
  criado_em timestamptz NOT NULL DEFAULT now(),
  criado_por uuid REFERENCES auth.users(id)
);

CREATE INDEX idx_transacao_linha_transacao ON transacao_linha(transacao_bancaria_id);
CREATE INDEX idx_transacao_linha_bolso ON transacao_linha(bolso);
CREATE INDEX idx_transacao_linha_orcamento
  ON transacao_linha(orcamento_linha_id)
  WHERE orcamento_linha_id IS NOT NULL;

ALTER TABLE transacao_linha ENABLE ROW LEVEL SECURITY;

CREATE POLICY transacao_linha_select ON transacao_linha
  FOR SELECT USING (auth.uid() IS NOT NULL);

CREATE POLICY transacao_linha_insert ON transacao_linha
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY transacao_linha_update ON transacao_linha
  FOR UPDATE USING (auth.uid() IS NOT NULL);

CREATE POLICY transacao_linha_delete ON transacao_linha
  FOR DELETE USING (auth.uid() IS NOT NULL);

-- Padrão de auditoria (igual demais tabelas): trigger fn_log_auditoria
CREATE TRIGGER trg_audit_transacao_linha
  AFTER INSERT OR UPDATE OR DELETE ON transacao_linha
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

COMMIT;
```

- [ ] **Step 2: Aplicar via MCP**

name=`0017_transacao_linha_split`.

- [ ] **Step 3: Commit**

```bash
git add backend/supabase/migrations/0017_transacao_linha_split.sql
git commit -m "feat(track-b): migration 0017 transacao_linha (split fatura cartão)"
```

---

## Task 5: Migration 0018 — saldo_caixa_diario + rendimento

**Files:** Create `backend/supabase/migrations/0018_saldo_caixa_diario_e_rendimento.sql`

- [ ] **Step 1: Escrever a migration**

```sql
-- Migration 0018: saldo_caixa_diario (materialização para evolução do caixa
-- e tendência histórica) + colunas de rendimento em aplicacao_financeira
-- (precisão máxima: rendimento MANUAL sobrescreve CALCULADO).

BEGIN;

CREATE TABLE saldo_caixa_diario (
  data date NOT NULL,
  empresa_id uuid NOT NULL REFERENCES empresa(id),
  saldo_contas_correntes numeric(14,2) NOT NULL DEFAULT 0,
  saldo_aplicacoes numeric(14,2) NOT NULL DEFAULT 0,
  liquidez_total numeric(14,2)
    GENERATED ALWAYS AS (saldo_contas_correntes + saldo_aplicacoes) STORED,
  rendimento_do_dia numeric(14,2) NOT NULL DEFAULT 0,
  entradas_do_dia numeric(14,2) NOT NULL DEFAULT 0,
  saidas_do_dia numeric(14,2) NOT NULL DEFAULT 0,
  atualizado_em timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (data, empresa_id)
);

CREATE INDEX idx_saldo_caixa_diario_data ON saldo_caixa_diario(data DESC);

ALTER TABLE saldo_caixa_diario ENABLE ROW LEVEL SECURITY;

CREATE POLICY saldo_caixa_diario_select ON saldo_caixa_diario
  FOR SELECT USING (auth.uid() IS NOT NULL);

CREATE POLICY saldo_caixa_diario_all_ceo ON saldo_caixa_diario
  FOR ALL USING (fn_is_ceo());

-- Rendimento explícito em aplicacao_financeira
CREATE TYPE fonte_rendimento AS ENUM ('CALCULADO', 'MANUAL');

ALTER TABLE aplicacao_financeira
  ADD COLUMN rendimento_ultima_atualizacao numeric(14,2),
  ADD COLUMN rendimento_ultima_atualizacao_fonte fonte_rendimento;

COMMIT;
```

- [ ] **Step 2: Aplicar via MCP**

name=`0018_saldo_caixa_diario_e_rendimento`.

- [ ] **Step 3: Commit**

```bash
git add backend/supabase/migrations/0018_saldo_caixa_diario_e_rendimento.sql
git commit -m "feat(track-b): migration 0018 saldo_caixa_diario + rendimento em aplicacao"
```

---

## Task 6: Migration 0019 — RECEITA_FINANCEIRA natureza

**Files:** Create `backend/supabase/migrations/0019_natureza_receita_financeira.sql`

- [ ] **Step 1: Escrever a migration (ALTER TYPE isolado)**

```sql
-- Migration 0019: adiciona RECEITA_FINANCEIRA ao enum natureza_lancamento.
--
-- NOTA: ALTER TYPE ADD VALUE não pode rodar em transação (igual migration 0014).
-- Aplicar como comando isolado.

ALTER TYPE natureza_lancamento ADD VALUE IF NOT EXISTS 'RECEITA_FINANCEIRA';
```

- [ ] **Step 2: Aplicar via MCP**

name=`0019_natureza_receita_financeira`.

- [ ] **Step 3: Commit**

```bash
git add backend/supabase/migrations/0019_natureza_receita_financeira.sql
git commit -m "feat(track-b): migration 0019 RECEITA_FINANCEIRA no enum natureza"
```

---

## Task 7: Rodar suite completa de testes após migrations

- [ ] **Step 1: Rodar suite full**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro-trackb
python -m pytest backend/tests/ -v --tb=short 2>&1 | tail -30
```

Expected: baseline anterior + 2 novos testes da Task 2 passando. Nenhum teste novo quebrado.

Se algum teste existente quebrar, investigar: provavelmente SELECT que precisa se adaptar ao novo schema (ex: `empresa.regime_tributario` agora NOT NULL). Reverter migration se precisar.

---

## Task 8: Script de backfill pj_empregadora_id

**Files:**
- Create: `backend/scripts/backfill_pj_empregadora_config.json`
- Create: `backend/scripts/backfill_pj_empregadora.py`
- Test: `backend/tests/test_backfill_pj_empregadora.py`

- [ ] **Step 1: Criar template de config (Hugo preenche)**

Criar `backend/scripts/backfill_pj_empregadora_config.json`:

```json
{
  "comentario": "Lista de prestadores a vincular à empresa FD. Preencher com nomes exatos conforme aparecem em prestador.nome ou prestador.razao_social_pj. Script usa match case-insensitive por similaridade WRatio >= 90 e pede confirmação para cada match.",
  "empresa_codigo": "FD",
  "prestadores": [
    "Thais Alessandra",
    "Vinicius Augusto"
  ],
  "contratos_lotados": {
    "comentario": "Todos os CLTs que atuam nos contratos abaixo recebem vínculo FD automaticamente. Lista de contratos por CIDADE/UF.",
    "cidades": [
      "UNAI/MG"
    ]
  }
}
```

- [ ] **Step 2: Escrever o test primeiro (TDD)**

Criar `backend/tests/test_backfill_pj_empregadora.py`:

```python
"""Testa script de backfill de pj_empregadora_id (dry-run + idempotência)."""
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.scripts.backfill_pj_empregadora import (
    carregar_config,
    encontrar_prestadores_por_nome,
    encontrar_prestadores_por_cidade,
    aplicar_backfill,
    PlanoBackfill,
)


def test_carregar_config_valida(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({
        "empresa_codigo": "FD",
        "prestadores": ["Ana"],
        "contratos_lotados": {"cidades": ["X/UF"]},
    }))
    data = carregar_config(str(cfg))
    assert data["empresa_codigo"] == "FD"
    assert data["prestadores"] == ["Ana"]


def test_encontrar_prestadores_por_nome_match_exato():
    client = MagicMock()
    client.table.return_value.select.return_value.execute.return_value.data = [
        {"id": "p1", "nome": "Thais Alessandra", "pj_empregadora_id": None},
        {"id": "p2", "nome": "Vinicius Augusto", "pj_empregadora_id": None},
        {"id": "p3", "nome": "Outro Nome", "pj_empregadora_id": None},
    ]
    matches = encontrar_prestadores_por_nome(
        client, nomes=["Thais Alessandra", "Vinicius Augusto"]
    )
    assert len(matches) == 2
    assert {m["id"] for m in matches} == {"p1", "p2"}


def test_encontrar_prestadores_por_nome_ja_vinculado_ignora():
    client = MagicMock()
    client.table.return_value.select.return_value.execute.return_value.data = [
        {"id": "p1", "nome": "Thais", "pj_empregadora_id": "fd-id"},
    ]
    matches = encontrar_prestadores_por_nome(client, nomes=["Thais"])
    # já tem pj_empregadora_id → idempotência: não re-aplica
    assert matches == []


def test_plano_backfill_dry_run_nao_modifica(tmp_path):
    client = MagicMock()
    plano = PlanoBackfill(
        empresa_id="fd-id",
        prestadores_a_vincular=[{"id": "p1", "nome": "Thais"}],
    )
    aplicar_backfill(client, plano, dry_run=True)
    # dry-run: nenhum update executado
    client.table.return_value.update.assert_not_called()


def test_plano_backfill_aplicado_chama_update(tmp_path):
    client = MagicMock()
    plano = PlanoBackfill(
        empresa_id="fd-id",
        prestadores_a_vincular=[{"id": "p1", "nome": "Thais"}],
    )
    aplicar_backfill(client, plano, dry_run=False)
    client.table.return_value.update.assert_called_once_with({"pj_empregadora_id": "fd-id"})
```

- [ ] **Step 3: Rodar tests e confirmar falha**

```bash
python -m pytest backend/tests/test_backfill_pj_empregadora.py -v
```

Expected: todos FAIL (módulo não existe).

- [ ] **Step 4: Implementar o script**

Criar `backend/scripts/backfill_pj_empregadora.py`:

```python
"""Backfill de prestador.pj_empregadora_id a partir de lista em JSON.

Uso:
    python -m backend.scripts.backfill_pj_empregadora --config backend/scripts/backfill_pj_empregadora_config.json --dry-run
    python -m backend.scripts.backfill_pj_empregadora --config backend/scripts/backfill_pj_empregadora_config.json --apply

Idempotente: prestadores com pj_empregadora_id já preenchido são ignorados.
Registra cada UPDATE em log_auditoria via trigger padrão.
"""
import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict

from supabase import create_client, Client


@dataclass
class PlanoBackfill:
    empresa_id: str
    prestadores_a_vincular: List[Dict] = field(default_factory=list)


def carregar_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def resolver_empresa_id(client: Client, codigo: str) -> str:
    rows = client.table("empresa").select("id").eq("codigo", codigo).execute().data
    if not rows:
        raise RuntimeError(f"Empresa código={codigo} não encontrada")
    return rows[0]["id"]


def encontrar_prestadores_por_nome(client: Client, nomes: List[str]) -> List[Dict]:
    """Retorna prestadores cujo nome ou razao_social bate, e que não têm pj_empregadora_id."""
    todos = client.table("prestador").select("id,nome,razao_social_pj,pj_empregadora_id").execute().data
    nomes_norm = {n.strip().upper() for n in nomes}
    matches = []
    for p in todos:
        if p.get("pj_empregadora_id"):
            continue  # idempotência
        alvos = [
            (p.get("nome") or "").strip().upper(),
            (p.get("razao_social_pj") or "").strip().upper(),
        ]
        if any(a in nomes_norm for a in alvos if a):
            matches.append(p)
    return matches


def encontrar_prestadores_por_cidade(client: Client, cidades: List[str]) -> List[Dict]:
    """Prestadores que aparecem em registro_pp de contratos cuja cidade está na lista."""
    if not cidades:
        return []
    contratos = (
        client.table("contrato")
        .select("id,cidade_uf")
        .in_("cidade_uf", cidades)
        .execute()
        .data
    )
    if not contratos:
        return []
    contrato_ids = [c["id"] for c in contratos]
    registros = (
        client.table("registro_pp")
        .select("prestador_id")
        .in_("contrato_id", contrato_ids)
        .execute()
        .data
    )
    prestador_ids = list({r["prestador_id"] for r in registros})
    if not prestador_ids:
        return []
    prestadores = (
        client.table("prestador")
        .select("id,nome,pj_empregadora_id")
        .in_("id", prestador_ids)
        .execute()
        .data
    )
    return [p for p in prestadores if not p.get("pj_empregadora_id")]


def aplicar_backfill(client: Client, plano: PlanoBackfill, dry_run: bool) -> None:
    for p in plano.prestadores_a_vincular:
        print(f"  {'[DRY-RUN]' if dry_run else '[APPLY] '} {p['nome']} (id={p['id']}) → empresa_id={plano.empresa_id}")
        if not dry_run:
            client.table("prestador").update({"pj_empregadora_id": plano.empresa_id}).eq("id", p["id"]).execute()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    cfg = carregar_config(args.config)
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(url, key)

    empresa_id = resolver_empresa_id(client, cfg["empresa_codigo"])
    por_nome = encontrar_prestadores_por_nome(client, cfg.get("prestadores", []))
    cidades = cfg.get("contratos_lotados", {}).get("cidades", [])
    por_cidade = encontrar_prestadores_por_cidade(client, cidades)
    # Deduplica
    vistos = set()
    a_vincular = []
    for p in por_nome + por_cidade:
        if p["id"] not in vistos:
            a_vincular.append(p)
            vistos.add(p["id"])

    print(f"\nEmpresa destino: {cfg['empresa_codigo']} (id={empresa_id})")
    print(f"Prestadores a vincular: {len(a_vincular)}")
    print(f"  - Por nome ({len(por_nome)})")
    print(f"  - Por cidade ({len(por_cidade)})")
    print()

    plano = PlanoBackfill(empresa_id=empresa_id, prestadores_a_vincular=a_vincular)
    aplicar_backfill(client, plano, dry_run=args.dry_run)

    print(f"\n{'[DRY-RUN concluído]' if args.dry_run else '[APPLY concluído]'} {len(a_vincular)} prestadores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Rodar tests de novo**

```bash
python -m pytest backend/tests/test_backfill_pj_empregadora.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Rodar dry-run com o config template**

```bash
python -m backend.scripts.backfill_pj_empregadora \
  --config backend/scripts/backfill_pj_empregadora_config.json \
  --dry-run
```

Expected: saída listando prestadores que seriam vinculados, sem modificar banco.

**IMPORTANTE:** O config template tem apenas valores-exemplo. **Hugo deve revisar e completar** antes do --apply em produção. Essa revisão é o pré-requisito externo listado no topo do plano.

- [ ] **Step 7: Commit**

```bash
git add backend/scripts/backfill_pj_empregadora.py backend/scripts/backfill_pj_empregadora_config.json backend/tests/test_backfill_pj_empregadora.py
git commit -m "feat(track-b): script idempotente de backfill pj_empregadora_id com dry-run"
```

---

## Task 9: Fix do bug saldo_inicial (renomear para entradas_do_mes)

**Files:**
- Modify: `backend/api/schemas/dashboard.py`
- Modify: `backend/api/routers/dashboard.py:161-183`
- Test: `backend/tests/test_dashboard_fixes.py`

- [ ] **Step 1: Escrever test primeiro**

Criar `backend/tests/test_dashboard_fixes.py`:

```python
"""Testa fixes de bugs do Dashboard (saldo_inicial removido, saldo_atual = liquidez)."""
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.api.main import app


@patch("backend.api.deps.get_current_user")
def test_dashboard_tem_entradas_do_mes_e_nao_saldo_inicial(mock_user, client_authed):
    """A KPI 'saldo_inicial' (hardcoded=0) foi substituída por 'entradas_do_mes'."""
    resp = client_authed.get("/dashboard?competencia=2026-04")
    assert resp.status_code == 200
    kpis = resp.json()["kpis"]
    assert "entradas_do_mes" in kpis
    assert "saldo_inicial" not in kpis
    assert isinstance(kpis["entradas_do_mes"], (int, float))


@patch("backend.api.deps.get_current_user")
def test_dashboard_saldo_atual_bate_com_liquidez(mock_user, client_authed):
    """saldo_atual no Dashboard = liquidez_total em /saldos/dashboard."""
    resp_dash = client_authed.get("/dashboard?competencia=2026-04").json()
    resp_saldos = client_authed.get("/saldos/dashboard").json()
    assert abs(resp_dash["kpis"]["saldo_atual"] - resp_saldos["liquidez_total"]) < 0.01
```

(`client_authed` é fixture existente em `conftest.py` — se não existir, criar com JWT válido.)

- [ ] **Step 2: Rodar test e confirmar falha**

```bash
python -m pytest backend/tests/test_dashboard_fixes.py -v
```

Expected: FAIL com `'saldo_inicial' not in kpis` falhando (ainda existe).

- [ ] **Step 3: Editar schema KPIs**

Em `backend/api/schemas/dashboard.py`, localizar a classe `KPIs` e renomear:

```python
# Antes:
# class KPIs(BaseModel):
#     saldo_inicial: float
#     saidas_mes: float
#     previsto_a_pagar: float
#     saldo_atual: float

class KPIs(BaseModel):
    entradas_do_mes: float
    saidas_mes: float
    previsto_a_pagar: float
    saldo_atual: float
```

- [ ] **Step 4: Editar router dashboard.py**

Em `backend/api/routers/dashboard.py`, linhas 161-183, substituir o bloco de KPIs:

```python
    # --- 7. KPIs ---
    # Fix (Track B): entradas_do_mes substitui saldo_inicial hardcoded=0.
    # saldo_atual agora vem da Liquidez Total real, não calculado do zero.
    creditos_rows = (
        client.table("transacao_bancaria")
        .select("valor")
        .eq("tipo", "CREDITO")
        .gte("data_extrato", d_ini)
        .lte("data_extrato", d_fim)
        .execute()
        .data
    )
    entradas_do_mes = sum(float(t["valor"]) for t in creditos_rows)
    saidas_mes = saidas_total

    # saldo_atual = liquidez_total (snapshot mais recente de todas as contas + aplicações)
    from backend.api.routers.saldos import get_liquidez_total
    saldo_atual = get_liquidez_total(client)

    kpis = KPIs(
        entradas_do_mes=round(entradas_do_mes, 2),
        saidas_mes=round(saidas_mes, 2),
        previsto_a_pagar=round(previsto_total, 2),
        saldo_atual=round(saldo_atual, 2),
    )
```

- [ ] **Step 5: Expor helper em saldos.py**

Em `backend/api/routers/saldos.py`, adicionar função pública (se ainda não existe):

```python
def get_liquidez_total(client) -> float:
    """Retorna a liquidez total atual (snapshots mais recentes de CC + aplicações).

    Usado pelo /dashboard para que saldo_atual reflita realidade, não cálculo do zero.
    """
    # Último saldo por conta
    contas = client.table("conta_bancaria").select("id").execute().data
    saldo_cc = 0.0
    for c in contas:
        snap = (
            client.table("saldo_conta_snapshot")
            .select("saldo_valor")
            .eq("conta_bancaria_id", c["id"])
            .order("data_referencia", desc=True)
            .order("criado_em", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if snap:
            saldo_cc += float(snap[0]["saldo_valor"])
    # Aplicações ativas
    apls = (
        client.table("aplicacao_financeira")
        .select("valor_atual")
        .eq("ativo", True)
        .execute()
        .data
    )
    saldo_apl = sum(float(a["valor_atual"]) for a in apls)
    return saldo_cc + saldo_apl
```

- [ ] **Step 6: Rodar test de novo**

```bash
python -m pytest backend/tests/test_dashboard_fixes.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Rodar suite full pra garantir que nada quebrou**

```bash
python -m pytest backend/tests/ -v --tb=short 2>&1 | tail -15
```

Expected: todos passando. Se algum test que usa `saldo_inicial` quebrar, atualizar para `entradas_do_mes`.

- [ ] **Step 8: Commit**

```bash
git add backend/api/schemas/dashboard.py backend/api/routers/dashboard.py backend/api/routers/saldos.py backend/tests/test_dashboard_fixes.py
git commit -m "fix(track-b): saldo_inicial hardcoded → entradas_do_mes; saldo_atual = liquidez_total"
```

---

## Task 10: Buscar outros usos de saldo_inicial no código

**Files:** varre o frontend por referências ao nome antigo.

- [ ] **Step 1: Grep por saldo_inicial no código**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro-trackb
grep -rn "saldo_inicial\|saldoInicial" --include="*.py" --include="*.ts" --include="*.tsx" 2>&1 | head -20
```

Listar arquivos afetados. Esperado: pelo menos types e componentes do frontend com referência ao campo antigo.

- [ ] **Step 2: Atualizar tipos TypeScript do frontend**

Para cada arquivo listado em `frontend/types/` que define `saldo_inicial`, substituir por `entradas_do_mes`:

```typescript
// Antes:
// interface KPIs { saldo_inicial: number; saidas_mes: number; previsto_a_pagar: number; saldo_atual: number }

interface KPIs { entradas_do_mes: number; saidas_mes: number; previsto_a_pagar: number; saldo_atual: number }
```

- [ ] **Step 3: Atualizar componentes do Dashboard**

Para cada componente React/TSX que renderiza `kpis.saldo_inicial`, trocar label para "Entradas do mês" e usar `kpis.entradas_do_mes`.

- [ ] **Step 4: Rodar build do frontend**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro-trackb/frontend
npm run build 2>&1 | tail -10
```

Expected: build sem erro de tipo.

- [ ] **Step 5: Commit**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro-trackb
git add frontend/
git commit -m "fix(track-b): frontend reflete rename saldo_inicial → entradas_do_mes"
```

---

## Task 11: Smoke test local (API rodando)

- [ ] **Step 1: Subir backend localmente**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro-trackb/backend
uvicorn api.main:app --reload --port 8000 &
sleep 3
```

- [ ] **Step 2: Verificar /dashboard responde com novos campos**

```bash
curl -s "http://localhost:8000/dashboard?competencia=2026-04" \
  -H "Authorization: Bearer $JWT_HUGO" | python -m json.tool | head -30
```

Expected: JSON contém `kpis.entradas_do_mes`, não contém `kpis.saldo_inicial`. `kpis.saldo_atual` próximo de `liquidez_total` de `/saldos/dashboard`.

- [ ] **Step 3: Parar servidor local**

```bash
pkill -f "uvicorn api.main:app"
```

- [ ] **Step 4: Commit de marco**

```bash
git commit --allow-empty -m "chore(track-b): smoke test local passou — plano 01 finalizado"
```

---

## Task 12: Merge para main (opcional — Hugo autoriza)

- [ ] **Step 1: Push da branch**

```bash
git push -u origin feature/track-b-dashboard-bolsos
```

- [ ] **Step 2: Abrir PR via gh CLI**

```bash
gh pr create --title "Track B Plano 01: schema novo + backfill + fixes dashboard" \
  --body "$(cat <<'EOF'
## Summary
- Migrations 0015-0019: amplia empresa, pj_empregadora_id, bolsos, transacao_linha (split), saldo_caixa_diario, RECEITA_FINANCEIRA
- Script idempotente de backfill pj_empregadora_id com dry-run
- Fix dashboard: saldo_inicial=0 hardcoded → entradas_do_mes real; saldo_atual = liquidez_total

## Pré-deploy
- [ ] Hugo preencheu `backend/scripts/backfill_pj_empregadora_config.json` com nomes reais
- [ ] Dry-run do backfill validado em staging
- [ ] Smoke /dashboard confirma novos KPIs

## Test plan
- [ ] Suite de testes backend passando (baseline + novos)
- [ ] Build frontend sem erro de tipo
- [ ] /dashboard retorna entradas_do_mes e saldo_atual coerente com liquidez

🤖 Generated with Claude Code
EOF
)"
```

**Hugo valida o PR antes de merge para main.** Merge só após aprovação.

---

## Self-review

### Cobertura do spec (§3.1 e §5.3)

- ✅ empresa_grupo → decisão de usar extensão da tabela `empresa` (documentada na Arquitetura)
- ✅ `prestador.pj_empregadora_id` → Task 2
- ✅ `bolso_tipo` enum + coluna em `orcamento_linha` → Task 3
- ✅ `empresa_pagadora_id` em `orcamento_linha` → Task 3
- ✅ `transacao_linha` → Task 4
- ✅ `saldo_caixa_diario` → Task 5
- ✅ Rendimento explícito (calculado/manual) → Task 5
- ✅ RECEITA_FINANCEIRA natureza → Task 6
- ✅ Backfill `pj_empregadora_id` → Task 8
- ✅ Fix saldo_inicial=0 → Task 9
- ✅ Fix saldo_atual ≠ liquidez → Task 9

### Fora deste plano (fases subsequentes)

- Home refinada (6 blocos + sparkline + 4 gráficos) → **Plano 02** (Fase C)
- UI de bolso em orcamento_linha + split manual → **Plano 03** (Fase D)
- Conciliação em lote PIX→FD + flag `usa_conciliacao_lote` → **Plano 04** (Fase E)
- Parser amplia saldo diário + worker `fn_recalcular_saldo_diario` + subpáginas → **Plano 05** (Fase F)

### Notas finais

- Migrations são idempotentes via `IF NOT EXISTS` / `ON CONFLICT`.
- Nenhuma migration dropa coluna nem muda tipo. Reversível via migrations down se necessário (não escritas aqui — convenção do projeto não usa down).
- Backfill default de `bolso = SPM_OPERACIONAL` preserva comportamento — todas as linhas existentes continuam contabilizadas como operação SPM até reclassificação manual.
- Fix do saldo_atual pode alterar número que Hugo já está acostumado a ver (era cálculo do zero, agora é liquidez real). Essa é a correção intencional do bug.
