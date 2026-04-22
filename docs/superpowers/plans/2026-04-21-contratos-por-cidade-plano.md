# Contratos por Cidade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidar 115 contratos (1 por local_pp) em 15 contratos-cidade preservando 374 registro_pp + rodada ativa; entregar UI `/contratos` nova (lista + carry-over collapsible com 3 níveis de destaque por idade) + editor de campos extras.

**Architecture:** Migration transacional agrega em `(uf, cidade)`, parser PP passa a upsert por `(uf, cidade)`, router `/contratos` faz GROUP BY na query + novo endpoint `/contratos/anteriores` retorna carry-over. Frontend reorganiza tela lista em 2 blocos (atual + collapsible anteriores) e detalhe em 2 tabs (pagamentos + dados do contrato).

**Tech Stack:** Postgres (Supabase MCP `apply_migration`), FastAPI + supabase-py, Next.js 16 + React 19 + Tailwind v4 + axios.

**Spec:** `docs/superpowers/specs/2026-04-21-contratos-por-cidade-design.md`

---

## File Structure

### Backend — modificar

```
backend/supabase/migrations/0010_contratos_por_cidade.sql    (CRIAR)
backend/api/routers/rodadas.py                                 (modificar _garantir_contrato)
backend/api/routers/contratos_competencia.py                   (refactor completo)
backend/api/schemas/contrato_competencia.py                    (ampliar com carry-over + campos extras)
backend/tests/test_parser_contrato.py                          (CRIAR)
backend/tests/test_contratos_endpoints.py                      (CRIAR)
```

### Frontend — modificar

```
frontend/types/v2.ts                                           (adicionar tipos novos)
frontend/lib/api/contratos-competencia.ts                      (adicionar endpoints novos)
frontend/app/(authed)/contratos/page.tsx                       (reescrita)
frontend/app/(authed)/contratos/[id]/[competencia]/page.tsx    (reescrita com tabs)
frontend/components/contratos/tabela-cidade.tsx                (CRIAR — tabela da lista principal)
frontend/components/contratos/carry-over-section.tsx           (CRIAR — bloco collapsible)
frontend/components/contratos/editor-dados-contrato.tsx        (CRIAR — form campos extras)
```

---

## Task 1: Migration 0010 — schema + backfill + consolidação

**Files:**
- Create: `backend/supabase/migrations/0010_contratos_por_cidade.sql`

Esta migration é aplicada via **Supabase MCP `apply_migration`** (ambiente compartilhado com FaturaAI — `[ANCORADA] 24`). Rodar `list_tables` antes pra confirmar nenhuma colisão.

- [ ] **Step 1: Verificar nenhuma colisão no schema (FaturaAI coabita)**

Rodar via MCP:
```
mcp__claude_ai_Supabase__list_tables(project_id="mkxehqhikcuykaxnpxff", schemas=["public"])
```

Validar: tabelas `contrato`, `registro_pp` existem. Nenhuma tabela nova sendo criada nesta migration (só ALTER). Sem colisão esperada.

- [ ] **Step 2: Criar arquivo de migration**

```sql
-- backend/supabase/migrations/0010_contratos_por_cidade.sql
-- Modelo: 1 contrato = 1 (uf, cidade). Consolida artefato do parser (115 → 15).

BEGIN;

-- ========================================================
-- Colunas novas em `contrato`
-- ========================================================
ALTER TABLE contrato ADD COLUMN uf text;
ALTER TABLE contrato ADD COLUMN cidade text;
ALTER TABLE contrato ADD COLUMN nome_oficial text;
ALTER TABLE contrato ADD COLUMN valor_faturamento_mensal numeric(14,2);
ALTER TABLE contrato ADD COLUMN retencao_tributaria_pct numeric(5,2);
ALTER TABLE contrato ADD COLUMN observacoes text;

-- `registro_pp` ganha local_pp (preserva sub-local pro detalhe)
ALTER TABLE registro_pp ADD COLUMN local_pp text;

-- ========================================================
-- Backfill uf + cidade + local_pp
-- ========================================================

-- Extrai UF e cidade do local_pp atual, normalizando separador `–` → `-`
UPDATE contrato
SET 
  uf = upper(trim(split_part(regexp_replace(local_pp, '–', '-', 'g'), ' - ', 1))),
  cidade = upper(trim(split_part(regexp_replace(local_pp, '–', '-', 'g'), ' - ', 2)))
WHERE local_pp IS NOT NULL;

-- Backfill local_pp em registro_pp (tudo após "UF - CIDADE - ")
-- Trata separador –; pega partes 3+ do split
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

-- ========================================================
-- Consolidação de duplicatas (normaliza acento pro group)
-- ========================================================

-- Coluna temporária pra matching sem acento
ALTER TABLE contrato ADD COLUMN cidade_norm text;
UPDATE contrato SET cidade_norm = 
  translate(upper(cidade), 
    'ÃÁÀÂÄÉÊÈËÍÎÌÏÓÔÒÖÚÛÙÜÇÑ',
    'AAAAAEEEEIIIIOOOOUUUUCN');

-- Pra cada (uf, cidade_norm), escolhe menor id como "principal"
WITH principais AS (
  SELECT uf, cidade_norm, MIN(id) AS id_principal
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

-- Deleta contratos duplicados (sem registro_pp apontando agora)
DELETE FROM contrato
WHERE id NOT IN (SELECT DISTINCT contrato_id FROM registro_pp WHERE contrato_id IS NOT NULL);

-- ========================================================
-- NOT NULL + UNIQUE + DROP local_pp
-- ========================================================

ALTER TABLE contrato ALTER COLUMN uf SET NOT NULL;
ALTER TABLE contrato ALTER COLUMN cidade SET NOT NULL;
ALTER TABLE contrato ALTER COLUMN cidade_norm SET NOT NULL;

CREATE UNIQUE INDEX unique_uf_cidade_norm ON contrato (uf, cidade_norm);

-- local_pp passa a viver em registro_pp, não em contrato
ALTER TABLE contrato DROP COLUMN local_pp;

-- Recria trigger de auditoria se houver referência ao local_pp
-- (validar antes de rodar — trigger 0001 referencia local_pp? se sim, ajustar)

COMMIT;

-- ========================================================
-- Validação pós-migration (rodar manualmente depois do COMMIT)
-- ========================================================
-- SELECT count(*) FROM contrato;                 -- deve retornar ~15
-- SELECT count(*) FROM registro_pp;              -- deve retornar 374 (inalterado)
-- SELECT count(*) FROM registro_pp WHERE contrato_id NOT IN (SELECT id FROM contrato);  -- deve retornar 0 (zero órfãos)
-- SELECT count(*) FROM registro_pp WHERE local_pp IS NULL AND mes_competencia = '2026-02';  -- tem que ser baixo (poucos sem sub-local)
```

- [ ] **Step 3: Checar triggers que referenciem `contrato.local_pp`**

Via MCP `execute_sql`:
```sql
SELECT trigger_name, event_manipulation, action_statement
FROM information_schema.triggers
WHERE event_object_table = 'contrato';
```

Se algum trigger mencionar `local_pp`, ajustar ou remover ANTES do `DROP COLUMN local_pp`. Adicionar ajuste necessário dentro do `BEGIN/COMMIT` da migration acima.

- [ ] **Step 4: Aplicar migration via MCP**

Rodar:
```
mcp__claude_ai_Supabase__apply_migration(
  project_id="mkxehqhikcuykaxnpxff",
  name="0010_contratos_por_cidade",
  query="<conteúdo integral do arquivo .sql>"
)
```

- [ ] **Step 5: Validar pós-migration via MCP `execute_sql`**

```sql
-- Espera 15
SELECT count(*) FROM contrato;

-- Espera 374
SELECT count(*) FROM registro_pp;

-- Espera 0 (zero órfãos)
SELECT count(*) FROM registro_pp WHERE contrato_id NOT IN (SELECT id FROM contrato);

-- Espera cidades como 'IGUAPE', 'UNAI', etc.
SELECT uf, cidade, COUNT(*) AS registros_vinculados
FROM contrato c JOIN registro_pp r ON r.contrato_id = c.id
GROUP BY uf, cidade
ORDER BY uf, cidade;
```

Se qualquer validação falhar, ROLLBACK via Supabase dashboard (PITR) OU reverter manualmente. Se passar:

- [ ] **Step 6: Commit**

```bash
cd ~/spm-sistemafinanceiro
git add backend/supabase/migrations/0010_contratos_por_cidade.sql
git commit -m "feat(db): migration 0010 — 1 contrato = 1 (uf, cidade), consolida 115 → 15"
```

---

## Task 2: Parser `_garantir_contrato` (TDD)

**Files:**
- Modify: `backend/api/routers/rodadas.py:190-232` (função `_garantir_contrato`)
- Modify: `backend/src/pega_plantao.py` (persistidor — guardar local_pp em registro_pp)
- Create: `backend/tests/test_parser_contrato.py`

- [ ] **Step 1: Criar teste do split/normalização**

```python
# backend/tests/test_parser_contrato.py
"""Testes do parser de Local → (uf, cidade, local_sub)."""
import pytest
from backend.api.routers.rodadas import _parse_local_pp


def test_parse_simples():
    r = _parse_local_pp("SP - IGUAPE - UBS RURAL - ESF - SPM")
    assert r == ("SP", "IGUAPE", "UBS RURAL - ESF - SPM")


def test_parse_traco_longo():
    r = _parse_local_pp("SP – SERTÃOZINHO – UBS JAMAICA")
    assert r == ("SP", "SERTÃOZINHO", "UBS JAMAICA")


def test_parse_apenas_uf_cidade():
    r = _parse_local_pp("PR - LONDRINA")
    assert r == ("PR", "LONDRINA", None)


def test_parse_mixed_separators():
    r = _parse_local_pp("MG - UNAI – HOSPITAL MUNC. - PEDIATRIA")
    assert r == ("MG", "UNAI", "HOSPITAL MUNC. - PEDIATRIA")


def test_parse_empty():
    with pytest.raises(ValueError, match="Local vazio"):
        _parse_local_pp("")


def test_parse_sem_cidade():
    with pytest.raises(ValueError, match="não tem UF e cidade"):
        _parse_local_pp("SP")


def test_normaliza_acento_match():
    from backend.api.routers.rodadas import _normaliza_cidade
    assert _normaliza_cidade("SERTÃOZINHO") == "SERTAOZINHO"
    assert _normaliza_cidade("SÃO JOÃO") == "SAO JOAO"
    assert _normaliza_cidade("IGUAPE") == "IGUAPE"
```

- [ ] **Step 2: Rodar testes — esperado FAIL**

```bash
cd ~/spm-sistemafinanceiro && source backend/.venv/bin/activate
pytest backend/tests/test_parser_contrato.py -v
```

Expected: `ImportError: cannot import name '_parse_local_pp'`.

- [ ] **Step 3: Implementar funções `_parse_local_pp` e `_normaliza_cidade`**

Adicionar em `backend/api/routers/rodadas.py` (antes de `_garantir_contrato`):

```python
def _normaliza_cidade(s: str) -> str:
    """Remove acentos + upper pra matching. Preserva grafia no display."""
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).upper()


def _parse_local_pp(local: str) -> tuple[str, str, str | None]:
    """
    Extrai (uf, cidade, local_sub) de 'UF - CIDADE - LOCAL - SUB - ...'.

    - Normaliza separador `–` (traço longo) → `-`.
    - uf: upper, 2 chars.
    - cidade: upper (preserva acentos).
    - local_sub: tudo após "UF - CIDADE - ", ou None se não houver.

    Raises ValueError se string vazia ou sem cidade.
    """
    import re
    local = (local or "").strip()
    if not local:
        raise ValueError("Local vazio")
    normalized = re.sub(r'–', '-', local)
    parts = [p.strip() for p in normalized.split(' - ')]
    if len(parts) < 2:
        raise ValueError(f"Local não tem UF e cidade separados por ' - ': {local!r}")
    uf = parts[0].upper()
    cidade = parts[1].upper()
    local_sub = ' - '.join(parts[2:]) if len(parts) > 2 else None
    return uf, cidade, local_sub
```

- [ ] **Step 4: Rodar testes — esperado PASS**

```bash
pytest backend/tests/test_parser_contrato.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Refatorar `_garantir_contrato` pra usar (uf, cidade)**

Substituir lógica atual (linhas ~190-232 de `rodadas.py`):

```python
def _garantir_contrato(client: Client, local_pp: str | None) -> tuple[str, str | None]:
    """
    Garante que existe contrato para o (uf, cidade) derivados de `local_pp`.
    Retorna (contrato_id, local_sub).

    Local_sub é o sub-local dentro da cidade (UBS RURAL, CAPS, etc.),
    guardado depois em registro_pp.local_pp.

    Se contrato (uf, cidade_norm) não existe, cria com tipo='PUBLICO'.
    Edição de campos extras (CNPJ, nome_oficial, etc.) fica pra tela detalhe.
    """
    if not local_pp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "registro de PP sem Local (coluna Local)"},
        )

    try:
        uf, cidade, local_sub = _parse_local_pp(local_pp)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Local inválido: {e}"},
        )

    cidade_norm = _normaliza_cidade(cidade)

    # Lookup contrato existente por (uf, cidade_norm)
    existing = (
        client.table("contrato")
        .select("id")
        .eq("uf", uf)
        .eq("cidade_norm", cidade_norm)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"], local_sub

    # Cria novo
    payload = {
        "uf": uf,
        "cidade": cidade,
        "nome": f"{uf} - {cidade}",
        "tipo": "PUBLICO",
        "status": "ATIVO",
    }
    inserted = client.table("contrato").insert(payload).execute()
    if not inserted.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"falha ao criar contrato ({uf}, {cidade})"},
        )
    return inserted.data[0]["id"], local_sub
```

**Observação:** `cidade_norm` é coluna tipo texto (não generated) porque foi criada via `UPDATE` na migration. Upsert precisa setar explicitamente:

Corrigir o `payload`:
```python
payload = {
    "uf": uf,
    "cidade": cidade,
    "cidade_norm": cidade_norm,
    "nome": f"{uf} - {cidade}",
    "tipo": "PUBLICO",
    "status": "ATIVO",
}
```

- [ ] **Step 6: Ajustar chamador em `persistir_rodada` pra propagar `local_sub` pro `registro_pp`**

Localizar em `backend/src/pega_plantao.py` onde `registro_pp` é inserido via `contrato_id = _garantir_contrato(client, local_pp)`. Trocar por:

```python
contrato_id, local_sub = _garantir_contrato(client, local_pp)
# ... resto do payload do registro_pp
payload["local_pp"] = local_sub  # guarda sub-local dentro da cidade
```

- [ ] **Step 7: Rodar suite completa do backend**

```bash
cd ~/spm-sistemafinanceiro && source backend/.venv/bin/activate
pytest backend/ -q
```

Expected: 74+7 = 81 passed (7 novos de parser contrato, 74 anteriores).

- [ ] **Step 8: Commit**

```bash
git add backend/api/routers/rodadas.py backend/src/pega_plantao.py backend/tests/test_parser_contrato.py
git commit -m "refactor(parser): _garantir_contrato usa (uf, cidade), local_sub em registro_pp"
```

---

## Task 3: Schemas Pydantic + endpoints do router

**Files:**
- Modify: `backend/api/schemas/contrato_competencia.py`
- Modify: `backend/api/routers/contratos_competencia.py`
- Create: `backend/tests/test_contratos_endpoints.py`

### Task 3a: Schemas Pydantic novos

- [ ] **Step 1: Atualizar `backend/api/schemas/contrato_competencia.py`**

```python
"""Schemas de contratos por cidade + carry-over + campos extras."""
from datetime import date
from typing import Optional
from pydantic import BaseModel


class ContratoCidadeListItem(BaseModel):
    """1 linha da tela lista /contratos."""
    id: str
    uf: str
    cidade: str
    competencia: str
    total: float
    total_pago: float
    saldo: float
    prestadores: int
    status: str  # "PAGO" | "PARCIAL" | "PENDENTE"


class ContratoAnteriorItem(BaseModel):
    """1 linha do carry-over (compete < atual, saldo > 0)."""
    contrato_id: str
    uf: str
    cidade: str
    competencia: str
    total_original: float
    total_pago: float
    saldo_aberto: float
    prestadores: int
    status: str
    idade_dias: int


class PrestadorLinhaDetalhe(BaseModel):
    """1 linha da tabela de detalhe do contrato (prestador × local × competência)."""
    prestador_id: str
    prestador_nome: str
    local: Optional[str]
    competencia: str
    total: float
    total_pago: float
    saldo: float
    status: str
    data_pagamento: Optional[date]


class ContratoDadosExtras(BaseModel):
    """Campos editáveis na tab 'Dados do contrato'."""
    nome_oficial: Optional[str] = None
    cnpj: Optional[str] = None
    tipo: Optional[str] = None  # "PUBLICO" | "PRIVADO"
    valor_faturamento_mensal: Optional[float] = None
    retencao_tributaria_pct: Optional[float] = None
    observacoes: Optional[str] = None


class ContratoDetalheOut(BaseModel):
    """Resposta GET /contratos/{id}/competencia/{mes}."""
    contrato_id: str
    uf: str
    cidade: str
    competencia: str
    total: float
    total_pago: float
    saldo: float
    prestadores_count: int
    registros_count: int
    linhas: list[PrestadorLinhaDetalhe]
    dados_extras: ContratoDadosExtras
```

- [ ] **Step 2: Commit schemas**

```bash
git add backend/api/schemas/contrato_competencia.py
git commit -m "feat(schema): schemas de contratos por cidade (lista + anteriores + detalhe + extras)"
```

### Task 3b: Endpoint `GET /contratos` agrupado

- [ ] **Step 3: Escrever teste de integração (skip se sem ambiente)**

```python
# backend/tests/test_contratos_endpoints.py
"""Testes dos endpoints de contratos (smoke via supabase-py mock leve)."""
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)


@pytest.mark.skip(reason="integração real — requer JWT + banco")
def test_listar_contratos_agrupa_por_cidade():
    """Lista deve retornar 1 linha por (uf, cidade) com soma de saldos."""
    resp = client.get("/contratos?competencia=2026-02", headers={"Authorization": "Bearer TEST"})
    assert resp.status_code == 200
    data = resp.json()
    # Com o seed consolidado (15 cidades), espera 15 contratos distintos
    assert len(data) == 15
    ufs = {row["uf"] for row in data}
    assert "MG" in ufs and "SP" in ufs and "PR" in ufs
    # Schema batea com ContratoCidadeListItem
    for row in data:
        assert "uf" in row and "cidade" in row and "saldo" in row and "status" in row


@pytest.mark.skip(reason="integração real")
def test_listar_anteriores():
    """/contratos/anteriores retorna competências < ate com saldo > 0."""
    resp = client.get("/contratos/anteriores?ate=2026-04", headers={"Authorization": "Bearer TEST"})
    assert resp.status_code == 200
    data = resp.json()
    for row in data:
        assert row["saldo_aberto"] > 0
        assert row["idade_dias"] >= 0
```

- [ ] **Step 4: Refactor `listar_contratos` pra agrupar por cidade**

Substituir função em `backend/api/routers/contratos_competencia.py`:

```python
from backend.api.schemas.contrato_competencia import (
    ContratoCidadeListItem, ContratoAnteriorItem, 
    ContratoDetalheOut, ContratoDadosExtras, PrestadorLinhaDetalhe,
)


@router.get("/contratos", response_model=list[ContratoCidadeListItem])
def listar_contratos(
    competencia: Optional[str] = None,
    current=Depends(get_current_user),
):
    """Lista contratos-cidade da competência. Agrupa saldo e status."""
    if not competencia:
        # Sem competência: lista vazia (força filtro)
        return []
    import re as _re
    if not _re.match(r"^\d{4}-\d{2}$", competencia):
        raise HTTPException(400, detail={"error": "competencia deve estar no formato YYYY-MM"})

    client = get_supabase_authed(current["jwt"])

    # 1. registro_pp da competência
    rpps = (
        client.table("registro_pp")
        .select("id,contrato_id,saldo_pp,prestador_id")
        .eq("mes_competencia", competencia)
        .execute()
        .data
    )
    if not rpps:
        return []

    # 2. Contratos envolvidos
    contrato_ids = list({r["contrato_id"] for r in rpps if r.get("contrato_id")})
    if not contrato_ids:
        return []
    contratos = (
        client.table("contrato")
        .select("id,uf,cidade")
        .in_("id", contrato_ids)
        .execute()
        .data
    )
    contrato_by_id = {c["id"]: c for c in contratos}

    # 3. Transações que apontam pros rpps (pra calcular total_pago)
    rpp_ids = [r["id"] for r in rpps]
    txs = (
        client.table("transacao_bancaria")
        .select("registro_pp_id,valor")
        .in_("registro_pp_id", rpp_ids)
        .execute()
        .data
    )
    pago_por_rpp: dict[str, float] = {}
    for t in txs:
        rpp_id = t.get("registro_pp_id")
        if rpp_id:
            pago_por_rpp[rpp_id] = pago_por_rpp.get(rpp_id, 0.0) + abs(float(t["valor"]))

    # 4. Agregar por contrato_id (1 linha por cidade)
    agreg: dict[str, dict] = {}
    for r in rpps:
        cid = r.get("contrato_id")
        if not cid or cid not in contrato_by_id:
            continue
        a = agreg.setdefault(cid, {
            "total": 0.0, "total_pago": 0.0, "prestadores": set(),
        })
        a["total"] += float(r["saldo_pp"])
        a["total_pago"] += pago_por_rpp.get(r["id"], 0.0)
        a["prestadores"].add(r["prestador_id"])

    # 5. Montar lista final
    out: list[ContratoCidadeListItem] = []
    for cid, a in agreg.items():
        c = contrato_by_id[cid]
        total = round(a["total"], 2)
        pago = round(a["total_pago"], 2)
        saldo = round(total - pago, 2)
        if pago >= total and total > 0:
            st = "PAGO"
        elif pago > 0:
            st = "PARCIAL"
        else:
            st = "PENDENTE"
        out.append(ContratoCidadeListItem(
            id=cid, uf=c["uf"], cidade=c["cidade"], competencia=competencia,
            total=total, total_pago=pago, saldo=saldo,
            prestadores=len(a["prestadores"]), status=st,
        ))
    out.sort(key=lambda x: -x.saldo)
    return out
```

- [ ] **Step 5: Rodar testes + smoke local**

```bash
pytest backend/tests/test_contratos_endpoints.py -v  # espera 2 skipped
# Smoke manual:
uvicorn backend.api.main:app --port 8888 &
sleep 3
curl -s http://localhost:8888/openapi.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('/contratos' in d['paths'])"
pkill -f "uvicorn backend.api.main:app --port 8888" 2>/dev/null
```

Expected: rota existe (retorno `True`).

- [ ] **Step 6: Commit endpoint listar**

```bash
git add backend/api/routers/contratos_competencia.py backend/tests/test_contratos_endpoints.py
git commit -m "feat(api): /contratos agrupa por (uf, cidade) em vez de local_pp"
```

### Task 3c: Endpoint `/contratos/anteriores`

- [ ] **Step 7: Adicionar endpoint de carry-over**

Após `listar_contratos` no mesmo arquivo:

```python
@router.get("/contratos/anteriores", response_model=list[ContratoAnteriorItem])
def listar_anteriores(
    ate: str,
    current=Depends(get_current_user),
):
    """Retorna contratos com saldo em aberto em competências < `ate`."""
    import re as _re
    from datetime import date
    if not _re.match(r"^\d{4}-\d{2}$", ate):
        raise HTTPException(400, detail={"error": "ate deve estar no formato YYYY-MM"})

    client = get_supabase_authed(current["jwt"])

    # 1. registro_pp com competência < ate
    rpps = (
        client.table("registro_pp")
        .select("id,contrato_id,saldo_pp,prestador_id,mes_competencia")
        .lt("mes_competencia", ate)
        .execute()
        .data
    )
    if not rpps:
        return []

    # 2. Contratos envolvidos
    contrato_ids = list({r["contrato_id"] for r in rpps if r.get("contrato_id")})
    contratos = (
        client.table("contrato").select("id,uf,cidade").in_("id", contrato_ids).execute().data
        if contrato_ids else []
    )
    contrato_by_id = {c["id"]: c for c in contratos}

    # 3. Total pago por rpp
    rpp_ids = [r["id"] for r in rpps]
    txs = (
        client.table("transacao_bancaria")
        .select("registro_pp_id,valor").in_("registro_pp_id", rpp_ids).execute().data
        if rpp_ids else []
    )
    pago_por_rpp: dict[str, float] = {}
    for t in txs:
        rid = t.get("registro_pp_id")
        if rid:
            pago_por_rpp[rid] = pago_por_rpp.get(rid, 0.0) + abs(float(t["valor"]))

    # 4. Agrega por (contrato_id, competencia); só retorna com saldo > 0
    agreg: dict[tuple, dict] = {}
    for r in rpps:
        cid = r.get("contrato_id")
        if not cid or cid not in contrato_by_id:
            continue
        key = (cid, r["mes_competencia"])
        a = agreg.setdefault(key, {
            "total": 0.0, "total_pago": 0.0, "prestadores": set(),
        })
        a["total"] += float(r["saldo_pp"])
        a["total_pago"] += pago_por_rpp.get(r["id"], 0.0)
        a["prestadores"].add(r["prestador_id"])

    # 5. Monta lista filtrando saldo > 0 + calcula idade_dias
    today = date.today()
    out: list[ContratoAnteriorItem] = []
    for (cid, comp), a in agreg.items():
        total = round(a["total"], 2)
        pago = round(a["total_pago"], 2)
        saldo = round(total - pago, 2)
        if saldo <= 0.01:  # pago ou quase
            continue
        if pago >= total and total > 0:
            st = "PAGO"
        elif pago > 0:
            st = "PARCIAL"
        else:
            st = "PENDENTE"
        # Idade = hoje - último dia do mês da competência
        y, m = map(int, comp.split("-"))
        from calendar import monthrange
        last_day = monthrange(y, m)[1]
        ref = date(y, m, last_day)
        idade = (today - ref).days
        c = contrato_by_id[cid]
        out.append(ContratoAnteriorItem(
            contrato_id=cid, uf=c["uf"], cidade=c["cidade"], competencia=comp,
            total_original=total, total_pago=pago, saldo_aberto=saldo,
            prestadores=len(a["prestadores"]), status=st, idade_dias=max(idade, 0),
        ))
    # Ordena do mais recente pro mais antigo (competência desc)
    out.sort(key=lambda x: x.competencia, reverse=True)
    return out
```

- [ ] **Step 8: Commit endpoint anteriores**

```bash
git add backend/api/routers/contratos_competencia.py
git commit -m "feat(api): /contratos/anteriores retorna carry-over com idade_dias"
```

### Task 3d: Endpoint `PATCH /contratos/{id}`

- [ ] **Step 9: Adicionar PATCH**

```python
@router.patch("/contratos/{contrato_id}", response_model=ContratoDadosExtras)
def editar_dados_contrato(
    contrato_id: UUID,
    payload: ContratoDadosExtras,
    current=Depends(get_current_user),
):
    """Atualiza campos extras do contrato (nome_oficial, cnpj, tipo, etc.).
    Campos ausentes não são alterados. Null explícito limpa."""
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, detail={"error": "Nada a atualizar"})
    client = get_supabase_authed(current["jwt"])
    r = client.table("contrato").update(updates).eq("id", str(contrato_id)).execute()
    if not r.data:
        raise HTTPException(404, detail={"error": "Contrato não encontrado"})
    d = r.data[0]
    return ContratoDadosExtras(
        nome_oficial=d.get("nome_oficial"),
        cnpj=d.get("cnpj"),
        tipo=d.get("tipo"),
        valor_faturamento_mensal=d.get("valor_faturamento_mensal"),
        retencao_tributaria_pct=d.get("retencao_tributaria_pct"),
        observacoes=d.get("observacoes"),
    )
```

- [ ] **Step 10: Commit PATCH**

```bash
git add backend/api/routers/contratos_competencia.py
git commit -m "feat(api): PATCH /contratos/{id} edita campos extras (CNPJ, nome_oficial, etc.)"
```

### Task 3e: Endpoint detalhe reformatado

- [ ] **Step 11: Reescrever endpoint `GET /contratos/{id}/competencia/{mes}`**

```python
@router.get(
    "/contratos/{contrato_id}/competencia/{competencia}",
    response_model=ContratoDetalheOut,
)
def detalhe(contrato_id: UUID, competencia: str, current=Depends(get_current_user)):
    """Detalhe do contrato-cidade na competência: KPIs + lista por (prestador × local)."""
    import re as _re
    if not _re.match(r"^\d{4}-\d{2}$", competencia):
        raise HTTPException(400, detail={"error": "competencia deve estar no formato YYYY-MM"})

    client = get_supabase_authed(current["jwt"])

    c = client.table("contrato").select(
        "id,uf,cidade,nome_oficial,cnpj,tipo,valor_faturamento_mensal,retencao_tributaria_pct,observacoes"
    ).eq("id", str(contrato_id)).limit(1).execute().data
    if not c:
        raise HTTPException(404, detail={"error": "Contrato não encontrado"})
    c = c[0]

    rpps = client.table("registro_pp").select(
        "id,prestador_id,saldo_pp,local_pp,prestador(nome)"
    ).eq("contrato_id", str(contrato_id)).eq("mes_competencia", competencia).execute().data

    rpp_ids = [r["id"] for r in rpps]
    txs = (
        client.table("transacao_bancaria")
        .select("registro_pp_id,valor,data_extrato").in_("registro_pp_id", rpp_ids).execute().data
        if rpp_ids else []
    )
    pago_por_rpp: dict[str, float] = {}
    data_max_por_rpp: dict[str, str] = {}
    for t in txs:
        rid = t.get("registro_pp_id")
        if rid:
            pago_por_rpp[rid] = pago_por_rpp.get(rid, 0.0) + abs(float(t["valor"]))
            d = str(t["data_extrato"])
            if rid not in data_max_por_rpp or d > data_max_por_rpp[rid]:
                data_max_por_rpp[rid] = d

    linhas: list[PrestadorLinhaDetalhe] = []
    total_sum = 0.0
    pago_sum = 0.0
    prestadores_set = set()
    for r in rpps:
        total = float(r["saldo_pp"])
        pago = pago_por_rpp.get(r["id"], 0.0)
        saldo = total - pago
        if pago >= total and total > 0:
            st = "PAGO"
        elif pago > 0:
            st = "PARCIAL"
        else:
            st = "PENDENTE"
        pd = data_max_por_rpp.get(r["id"])
        prest = r.get("prestador")
        nome = prest["nome"] if isinstance(prest, dict) else (prest[0]["nome"] if isinstance(prest, list) and prest else "—")
        linhas.append(PrestadorLinhaDetalhe(
            prestador_id=r["prestador_id"],
            prestador_nome=nome,
            local=r.get("local_pp"),
            competencia=competencia,
            total=round(total, 2),
            total_pago=round(pago, 2),
            saldo=round(saldo, 2),
            status=st,
            data_pagamento=pd,
        ))
        total_sum += total
        pago_sum += pago
        prestadores_set.add(r["prestador_id"])

    return ContratoDetalheOut(
        contrato_id=c["id"], uf=c["uf"], cidade=c["cidade"], competencia=competencia,
        total=round(total_sum, 2), total_pago=round(pago_sum, 2),
        saldo=round(total_sum - pago_sum, 2),
        prestadores_count=len(prestadores_set),
        registros_count=len(rpps),
        linhas=linhas,
        dados_extras=ContratoDadosExtras(
            nome_oficial=c.get("nome_oficial"),
            cnpj=c.get("cnpj"),
            tipo=c.get("tipo"),
            valor_faturamento_mensal=c.get("valor_faturamento_mensal"),
            retencao_tributaria_pct=c.get("retencao_tributaria_pct"),
            observacoes=c.get("observacoes"),
        ),
    )
```

- [ ] **Step 12: Rodar pytest completo + smoke**

```bash
pytest backend/ -q
# Expected: 81+ passed (novos skip 2 de integração)
```

- [ ] **Step 13: Commit final da Task 3**

```bash
git add backend/api/routers/contratos_competencia.py
git commit -m "feat(api): detalhe contrato agrupado por (prestador × local) + dados_extras"
```

---

## Task 4: Frontend — types + API client

**Files:**
- Modify: `frontend/types/v2.ts`
- Modify: `frontend/lib/api/contratos-competencia.ts`

- [ ] **Step 1: Adicionar tipos novos em `frontend/types/v2.ts`**

Adicionar ao final do arquivo:

```typescript
// Contratos por cidade (Track C)
export interface ContratoCidadeListItem {
  id: string
  uf: string
  cidade: string
  competencia: string
  total: number
  total_pago: number
  saldo: number
  prestadores: number
  status: "PAGO" | "PARCIAL" | "PENDENTE"
}

export interface ContratoAnteriorItem {
  contrato_id: string
  uf: string
  cidade: string
  competencia: string
  total_original: number
  total_pago: number
  saldo_aberto: number
  prestadores: number
  status: "PAGO" | "PARCIAL" | "PENDENTE"
  idade_dias: number
}

export interface PrestadorLinhaDetalhe {
  prestador_id: string
  prestador_nome: string
  local: string | null
  competencia: string
  total: number
  total_pago: number
  saldo: number
  status: "PAGO" | "PARCIAL" | "PENDENTE"
  data_pagamento: string | null
}

export interface ContratoDadosExtras {
  nome_oficial?: string | null
  cnpj?: string | null
  tipo?: "PUBLICO" | "PRIVADO" | null
  valor_faturamento_mensal?: number | null
  retencao_tributaria_pct?: number | null
  observacoes?: string | null
}

export interface ContratoDetalheOut {
  contrato_id: string
  uf: string
  cidade: string
  competencia: string
  total: number
  total_pago: number
  saldo: number
  prestadores_count: number
  registros_count: number
  linhas: PrestadorLinhaDetalhe[]
  dados_extras: ContratoDadosExtras
}
```

- [ ] **Step 2: Atualizar `frontend/lib/api/contratos-competencia.ts`**

Substituir conteúdo inteiro:

```typescript
import { apiClient } from "@/lib/api"
import type {
  ContratoCidadeListItem,
  ContratoAnteriorItem,
  ContratoDetalheOut,
  ContratoDadosExtras,
} from "@/types/v2"

export async function listarContratos(
  params: { competencia?: string } = {}
): Promise<ContratoCidadeListItem[]> {
  const { data } = await apiClient.get<ContratoCidadeListItem[]>("/contratos", { params })
  return data
}

export async function listarContratosAnteriores(
  ate: string
): Promise<ContratoAnteriorItem[]> {
  const { data } = await apiClient.get<ContratoAnteriorItem[]>("/contratos/anteriores", {
    params: { ate },
  })
  return data
}

export async function fetchContratoCompetencia(
  contrato_id: string,
  competencia: string
): Promise<ContratoDetalheOut> {
  const { data } = await apiClient.get<ContratoDetalheOut>(
    `/contratos/${contrato_id}/competencia/${competencia}`
  )
  return data
}

export async function editarDadosContrato(
  contrato_id: string,
  patch: ContratoDadosExtras
): Promise<ContratoDadosExtras> {
  const { data } = await apiClient.patch<ContratoDadosExtras>(
    `/contratos/${contrato_id}`,
    patch
  )
  return data
}
```

- [ ] **Step 3: Rodar build do frontend pra validar tipos**

```bash
cd ~/spm-sistemafinanceiro/frontend && npm run build 2>&1 | tail -20
```

Expected: build sucesso, zero erro de tipo.

- [ ] **Step 4: Commit**

```bash
cd ~/spm-sistemafinanceiro
git add frontend/types/v2.ts frontend/lib/api/contratos-competencia.ts
git commit -m "feat(frontend): types + api client pra contratos por cidade"
```

---

## Task 5: Frontend — tela lista `/contratos` com carry-over

**Files:**
- Create: `frontend/components/contratos/tabela-cidade.tsx`
- Create: `frontend/components/contratos/carry-over-section.tsx`
- Modify: `frontend/app/(authed)/contratos/page.tsx`

- [ ] **Step 1: Criar componente `tabela-cidade.tsx`**

```tsx
"use client"
import type { ContratoCidadeListItem } from "@/types/v2"
import { formatBRL } from "@/lib/format"
import Link from "next/link"

interface Props {
  itens: ContratoCidadeListItem[]
  competencia: string
}

const STATUS_STYLE: Record<string, string> = {
  PAGO: "bg-emerald-100 text-emerald-800",
  PARCIAL: "bg-blue-100 text-blue-800",
  PENDENTE: "bg-amber-100 text-amber-800",
}

export function TabelaCidade({ itens, competencia }: Props) {
  if (!itens.length) {
    return (
      <div className="p-6 text-sm text-slate-500 bg-white">
        Sem contratos em {competencia}.
      </div>
    )
  }
  const totalGeral = itens.reduce((s, i) => s + i.saldo, 0)
  return (
    <div className="bg-white">
      <table className="w-full text-sm">
        <thead className="bg-slate-100 border-b-2 border-slate-300">
          <tr>
            <th className="px-3.5 py-2.5 text-left text-[11px] uppercase text-slate-600 font-semibold">Contrato</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Prest.</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Total</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Pago</th>
            <th className="px-3.5 py-2.5 text-right text-[11px] uppercase text-slate-600 font-semibold">Saldo</th>
            <th className="px-3.5 py-2.5 text-center text-[11px] uppercase text-slate-600 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {itens.map(it => (
            <tr key={it.id} className="border-b border-slate-200 hover:bg-slate-50">
              <td className="px-3.5 py-2.5 font-semibold text-slate-900">
                <Link href={`/contratos/${it.id}/${competencia}`} className="hover:underline">
                  {it.uf} - {it.cidade} - {formatCompetenciaCurta(it.competencia)}
                </Link>
              </td>
              <td className="px-3.5 py-2.5 text-right text-slate-600">{it.prestadores}</td>
              <td className="px-3.5 py-2.5 text-right">{formatBRL(it.total)}</td>
              <td className="px-3.5 py-2.5 text-right text-slate-500">{formatBRL(it.total_pago)}</td>
              <td className="px-3.5 py-2.5 text-right font-semibold">{formatBRL(it.saldo)}</td>
              <td className="px-3.5 py-2.5 text-center">
                <span className={`inline-block text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${STATUS_STYLE[it.status]}`}>
                  {it.status[0] + it.status.slice(1).toLowerCase()}
                </span>
              </td>
            </tr>
          ))}
          <tr className="border-t-2 border-slate-300 bg-slate-50 font-bold">
            <td className="px-3.5 py-3">TOTAL · {itens.length} contratos</td>
            <td className="px-3.5 py-3 text-right">{itens.reduce((s, i) => s + i.prestadores, 0)}</td>
            <td className="px-3.5 py-3 text-right">{formatBRL(itens.reduce((s, i) => s + i.total, 0))}</td>
            <td className="px-3.5 py-3 text-right">{formatBRL(itens.reduce((s, i) => s + i.total_pago, 0))}</td>
            <td className="px-3.5 py-3 text-right text-red-900">{formatBRL(totalGeral)}</td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function formatCompetenciaCurta(comp: string): string {
  // "2026-04" → "04.26"
  const [y, m] = comp.split("-")
  return `${m}.${y.slice(2)}`
}
```

- [ ] **Step 2: Criar componente `carry-over-section.tsx`**

```tsx
"use client"
import { useState } from "react"
import type { ContratoAnteriorItem } from "@/types/v2"
import { formatBRL } from "@/lib/format"
import Link from "next/link"

interface Props {
  itens: ContratoAnteriorItem[]
}

function ageClass(dias: number): { bgFrom: string; bgTo: string; border: string; text: string; icon?: string; caps?: string } {
  if (dias >= 90) return {
    bgFrom: "#fca5a5", bgTo: "#fecaca",
    border: "#dc2626", text: "#7f1d1d",
    icon: "⚠️", caps: "URGENTE",
  }
  if (dias >= 60) return {
    bgFrom: "#fed7aa", bgTo: "#fef3c7",
    border: "#ea580c", text: "#9a3412",
    icon: "⏱",
  }
  return {
    bgFrom: "#e0e7ff", bgTo: "#e0e7ff",
    border: "#4f46e5", text: "#312e81",
  }
}

export function CarryOverSection({ itens }: Props) {
  const [open, setOpen] = useState(false)
  if (!itens.length) return null
  const totalSaldo = itens.reduce((s, i) => s + i.saldo_aberto, 0)

  // Agrupa por competencia (decrescente)
  const grupos = new Map<string, ContratoAnteriorItem[]>()
  for (const i of itens) {
    if (!grupos.has(i.competencia)) grupos.set(i.competencia, [])
    grupos.get(i.competencia)!.push(i)
  }
  const grupoOrdenado = [...grupos.entries()].sort(([a], [b]) => b.localeCompare(a))

  return (
    <div className="mt-5 border-t border-slate-200">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full px-5 py-3.5 flex items-center gap-2.5 cursor-pointer select-none hover:brightness-95 transition-all border-l-4"
        style={{
          background: "linear-gradient(90deg,#eef2ff 0%,#f8fafc 100%)",
          borderLeftColor: "#4f46e5",
        }}
      >
        <span
          className="inline-block text-indigo-700 text-sm transition-transform"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >▶</span>
        <h3 className="m-0 text-[13px] text-indigo-900 font-bold uppercase tracking-wide">
          Competências anteriores em aberto
        </h3>
        <span className="text-indigo-700 text-xs">
          · {grupos.size} competências · {itens.length} contratos
        </span>
        <span className="ml-auto text-[15px] font-bold text-indigo-700 tabular-nums">
          {formatBRL(totalSaldo)}
        </span>
      </button>

      {open && (
        <div>
          <table className="w-full text-sm border-collapse">
            <thead className="bg-indigo-100 border-b border-indigo-300">
              <tr>
                <th className="px-3.5 py-2 text-left text-[10px] uppercase text-indigo-900">Compet.</th>
                <th className="px-3.5 py-2 text-left text-[10px] uppercase text-indigo-900">Contrato</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-indigo-900">Prest.</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-indigo-900">Saldo original</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-indigo-900">Pago</th>
                <th className="px-3.5 py-2 text-right text-[10px] uppercase text-indigo-900">Saldo aberto</th>
                <th className="px-3.5 py-2 text-center text-[10px] uppercase text-indigo-900">Status</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {grupoOrdenado.map(([comp, itensGrupo]) => {
                const dias = Math.max(...itensGrupo.map(i => i.idade_dias))
                const style = ageClass(dias)
                const saldoGrupo = itensGrupo.reduce((s, i) => s + i.saldo_aberto, 0)
                const isDestaque = dias >= 60
                return (
                  <>
                    <tr key={`header-${comp}`}
                      style={isDestaque
                        ? { background: `linear-gradient(90deg,${style.bgFrom} 0%,${style.bgTo} 100%)`, borderTop: `${dias >= 90 ? 3 : 2}px solid ${style.border}` }
                        : { background: "#e0e7ff" }}>
                      <td colSpan={7} className={`${isDestaque ? "py-2.5" : "py-1.5"} px-3.5 font-bold`}
                        style={{ color: style.text, fontSize: isDestaque ? 13 : 12 }}>
                        {style.icon && <span className="mr-1.5" style={{ fontSize: dias >= 90 ? 16 : 14 }}>{style.icon}</span>}
                        {formatCompetenciaCurta(comp)} ·
                        <span style={{ fontSize: dias >= 90 ? 16 : isDestaque ? 14 : undefined }}>
                          {" "}{dias} dias em aberto{style.caps ? " — " + style.caps : ""}
                        </span>
                        {" "}· saldo {formatBRL(saldoGrupo)}
                        {dias >= 90 && <span className="ml-2.5 inline-block text-[10px] px-2.5 py-0.5 bg-red-900 text-white rounded-full font-bold">90+ DIAS</span>}
                      </td>
                    </tr>
                    {itensGrupo.map(it => (
                      <tr key={it.contrato_id + comp} className="border-b border-slate-200"
                        style={isDestaque ? { background: dias >= 90 ? "#fef2f2" : "#fff7ed" } : { background: "white" }}>
                        <td className="px-3.5 py-2 text-xs text-slate-600">{formatCompetenciaCurta(comp)}</td>
                        <td className="px-3.5 py-2 font-semibold text-slate-900">
                          <Link href={`/contratos/${it.contrato_id}/${comp}`} className="hover:underline">
                            {it.uf} - {it.cidade}
                          </Link>
                        </td>
                        <td className="px-3.5 py-2 text-right text-slate-600">{it.prestadores}</td>
                        <td className="px-3.5 py-2 text-right text-slate-500">{formatBRL(it.total_original)}</td>
                        <td className="px-3.5 py-2 text-right text-blue-800">{formatBRL(it.total_pago)}</td>
                        <td className="px-3.5 py-2 text-right font-bold text-red-900">{formatBRL(it.saldo_aberto)}</td>
                        <td className="px-3.5 py-2 text-center">
                          <span className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                            {it.status[0] + it.status.slice(1).toLowerCase()}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </>
                )
              })}
              <tr className="border-t-2 border-indigo-300 bg-indigo-100 font-bold">
                <td colSpan={5} className="px-3.5 py-2.5 text-indigo-900">Total em aberto (residual)</td>
                <td className="px-3.5 py-2.5 text-right text-indigo-700 tabular-nums">{formatBRL(totalSaldo)}</td>
                <td></td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function formatCompetenciaCurta(comp: string): string {
  const [y, m] = comp.split("-")
  return `${m}.${y.slice(2)}`
}
```

- [ ] **Step 3: Reescrever `frontend/app/(authed)/contratos/page.tsx`**

```tsx
"use client"
import { useEffect, useState } from "react"
import { useFilters } from "@/lib/filters-context"
import {
  listarContratos,
  listarContratosAnteriores,
} from "@/lib/api/contratos-competencia"
import { TabelaCidade } from "@/components/contratos/tabela-cidade"
import { CarryOverSection } from "@/components/contratos/carry-over-section"
import type { ContratoCidadeListItem, ContratoAnteriorItem } from "@/types/v2"
import { formatBRL } from "@/lib/format"
import { toast } from "sonner"

export default function ContratosPage() {
  const { competencia } = useFilters()
  const [itens, setItens] = useState<ContratoCidadeListItem[]>([])
  const [anteriores, setAnteriores] = useState<ContratoAnteriorItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      listarContratos({ competencia }),
      listarContratosAnteriores(competencia),
    ])
      .then(([atuais, ant]) => {
        if (!cancelled) {
          setItens(atuais)
          setAnteriores(ant)
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) toast.error("Falha: " + (e instanceof Error ? e.message : "erro"))
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [competencia])

  const saldoAtual = itens.reduce((s, i) => s + i.saldo, 0)
  const saldoAnteriores = anteriores.reduce((s, i) => s + i.saldo_aberto, 0)
  const totalGeral = saldoAtual + saldoAnteriores

  if (loading) return <div className="p-6 text-slate-500">Carregando contratos…</div>

  return (
    <div className="flex flex-col">
      <div className="bg-white px-5 pt-4 pb-2 flex items-center gap-2">
        <div className="w-1 h-4 bg-blue-600 rounded"></div>
        <h1 className="text-[13px] font-bold uppercase tracking-wide text-slate-900">
          Contratos de {formatCompetenciaCurta(competencia)}
        </h1>
        <span className="text-slate-500 text-xs">
          · {itens.length} contratos · {formatBRL(saldoAtual)} a pagar
        </span>
      </div>

      <TabelaCidade itens={itens} competencia={competencia} />
      <CarryOverSection itens={anteriores} />

      <div className="px-5 py-3.5 bg-slate-900 text-white flex items-center gap-3 text-sm">
        <span className="text-slate-400 uppercase text-[11px] tracking-wide">Total em aberto</span>
        <span className="text-slate-400 text-[11px]">(atual + anteriores)</span>
        <span className="ml-auto text-lg font-bold tabular-nums">{formatBRL(totalGeral)}</span>
      </div>
    </div>
  )
}

function formatCompetenciaCurta(comp: string): string {
  const [y, m] = comp.split("-")
  return `${m}.${y.slice(2)}`
}
```

- [ ] **Step 4: Rodar build**

```bash
cd ~/spm-sistemafinanceiro/frontend && npm run build 2>&1 | tail -15
```

Expected: build OK, rota `/contratos` gerada.

- [ ] **Step 5: Commit**

```bash
cd ~/spm-sistemafinanceiro
git add frontend/components/contratos/tabela-cidade.tsx frontend/components/contratos/carry-over-section.tsx frontend/app/\(authed\)/contratos/page.tsx
git commit -m "feat(frontend): tela /contratos nova — lista cidade + carry-over collapsible"
```

---

## Task 6: Frontend — tela detalhe com tabs + editor

**Files:**
- Create: `frontend/components/contratos/editor-dados-contrato.tsx`
- Modify: `frontend/app/(authed)/contratos/[id]/[competencia]/page.tsx`

- [ ] **Step 1: Criar `editor-dados-contrato.tsx`**

```tsx
"use client"
import { useState } from "react"
import type { ContratoDadosExtras } from "@/types/v2"
import { editarDadosContrato } from "@/lib/api/contratos-competencia"
import { toast } from "sonner"

interface Props {
  contratoId: string
  inicial: ContratoDadosExtras
  onSaved: (novos: ContratoDadosExtras) => void
}

export function EditorDadosContrato({ contratoId, inicial, onSaved }: Props) {
  const [nomeOficial, setNomeOficial] = useState(inicial.nome_oficial ?? "")
  const [cnpj, setCnpj] = useState(inicial.cnpj ?? "")
  const [tipo, setTipo] = useState(inicial.tipo ?? "PUBLICO")
  const [valorFat, setValorFat] = useState(inicial.valor_faturamento_mensal?.toString() ?? "")
  const [retencao, setRetencao] = useState(inicial.retencao_tributaria_pct?.toString() ?? "")
  const [obs, setObs] = useState(inicial.observacoes ?? "")
  const [saving, setSaving] = useState(false)

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const patch: ContratoDadosExtras = {
        nome_oficial: nomeOficial || null,
        cnpj: cnpj || null,
        tipo: (tipo as "PUBLICO" | "PRIVADO") || null,
        valor_faturamento_mensal: valorFat ? parseFloat(valorFat.replace(",", ".")) : null,
        retencao_tributaria_pct: retencao ? parseFloat(retencao.replace(",", ".")) : null,
        observacoes: obs || null,
      }
      const saved = await editarDadosContrato(contratoId, patch)
      toast.success("Dados salvos")
      onSaved(saved)
    } catch (err) {
      toast.error("Falha: " + (err instanceof Error ? err.message : "erro"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSave} className="space-y-3 max-w-2xl">
      <div>
        <label className="text-xs text-slate-600 block mb-1">Nome oficial</label>
        <input value={nomeOficial} onChange={e => setNomeOficial(e.target.value)} placeholder="Prefeitura Municipal de…" className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-slate-600 block mb-1">CNPJ</label>
          <input value={cnpj} onChange={e => setCnpj(e.target.value)} placeholder="00.000.000/0000-00" className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
        </div>
        <div>
          <label className="text-xs text-slate-600 block mb-1">Tipo</label>
          <select value={tipo} onChange={e => setTipo(e.target.value)} className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm">
            <option value="PUBLICO">Público</option>
            <option value="PRIVADO">Privado</option>
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-slate-600 block mb-1">Valor faturamento mensal (R$)</label>
          <input type="number" step="0.01" value={valorFat} onChange={e => setValorFat(e.target.value)} className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
        </div>
        <div>
          <label className="text-xs text-slate-600 block mb-1">Retenção tributária (%)</label>
          <input type="number" step="0.01" value={retencao} onChange={e => setRetencao(e.target.value)} className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
        </div>
      </div>
      <div>
        <label className="text-xs text-slate-600 block mb-1">Observações</label>
        <textarea value={obs} onChange={e => setObs(e.target.value)} rows={3} className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
      </div>
      <div className="flex justify-end">
        <button type="submit" disabled={saving} className="px-3.5 py-1.5 bg-slate-900 text-white rounded text-sm disabled:opacity-50">
          {saving ? "Salvando…" : "Salvar"}
        </button>
      </div>
    </form>
  )
}
```

- [ ] **Step 2: Reescrever `frontend/app/(authed)/contratos/[id]/[competencia]/page.tsx`**

```tsx
"use client"
import { useEffect, useState, use } from "react"
import { fetchContratoCompetencia } from "@/lib/api/contratos-competencia"
import { EditorDadosContrato } from "@/components/contratos/editor-dados-contrato"
import type { ContratoDetalheOut, ContratoDadosExtras } from "@/types/v2"
import { formatBRL } from "@/lib/format"
import Link from "next/link"
import { toast } from "sonner"

const STATUS_STYLE: Record<string, string> = {
  PAGO: "bg-emerald-100 text-emerald-800",
  PARCIAL: "bg-blue-100 text-blue-800",
  PENDENTE: "bg-amber-100 text-amber-800",
}

export default function ContratoDetalhePage({ params }: {
  params: Promise<{ id: string; competencia: string }>
}) {
  const { id, competencia } = use(params)
  const [data, setData] = useState<ContratoDetalheOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<"pagamentos" | "dados">("pagamentos")

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchContratoCompetencia(id, competencia)
      .then(d => { if (!cancelled) setData(d) })
      .catch((e: unknown) => {
        if (!cancelled) toast.error("Falha: " + (e instanceof Error ? e.message : "erro"))
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [id, competencia])

  function onSavedExtras(novos: ContratoDadosExtras) {
    if (data) setData({ ...data, dados_extras: novos })
  }

  if (loading) return <div className="p-6 text-slate-500">Carregando…</div>
  if (!data) return <div className="p-6 text-slate-500">Contrato não encontrado.</div>

  return (
    <div className="p-5 space-y-4">
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <Link href="/contratos" className="hover:underline">← Contratos</Link>
        <span>/</span>
        <span className="font-medium">{data.uf} - {data.cidade}</span>
        <span>/</span>
        <span>{formatCompetenciaCurta(data.competencia)}</span>
      </div>

      <div className="flex gap-0 border-b-2 border-slate-200 -mx-5 px-5">
        <button onClick={() => setTab("pagamentos")}
          className={tab === "pagamentos"
            ? "py-2.5 px-4 border-b-2 border-blue-500 -mb-0.5 text-blue-900 font-semibold text-sm"
            : "py-2.5 px-4 text-slate-500 text-sm hover:text-slate-700"}>
          Pagamentos
        </button>
        <button onClick={() => setTab("dados")}
          className={tab === "dados"
            ? "py-2.5 px-4 border-b-2 border-blue-500 -mb-0.5 text-blue-900 font-semibold text-sm"
            : "py-2.5 px-4 text-slate-500 text-sm hover:text-slate-700"}>
          Dados do contrato
        </button>
      </div>

      {tab === "pagamentos" && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-slate-900 text-white rounded px-3.5 py-2.5">
              <div className="text-[10px] uppercase text-slate-400 tracking-wide">Total</div>
              <div className="text-base font-bold mt-1 tabular-nums">{formatBRL(data.total)}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded px-3.5 py-2.5">
              <div className="text-[10px] uppercase text-slate-500 tracking-wide">Total Pago</div>
              <div className="text-base font-bold mt-1 tabular-nums">{formatBRL(data.total_pago)}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded px-3.5 py-2.5">
              <div className="text-[10px] uppercase text-slate-500 tracking-wide">Saldo</div>
              <div className="text-base font-bold mt-1 tabular-nums text-red-900">{formatBRL(data.saldo)}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded px-3.5 py-2.5">
              <div className="text-[10px] uppercase text-slate-500 tracking-wide">Prestadores</div>
              <div className="text-base font-bold mt-1">{data.prestadores_count} · {data.registros_count} reg.</div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-slate-100 border-b-2 border-slate-300">
                <tr>
                  <th className="px-2.5 py-2 text-left text-[10px] uppercase text-slate-600">Competência</th>
                  <th className="px-2.5 py-2 text-left text-[10px] uppercase text-slate-600">Prestador</th>
                  <th className="px-2.5 py-2 text-left text-[10px] uppercase text-slate-600">Local</th>
                  <th className="px-2.5 py-2 text-right text-[10px] uppercase text-slate-600">Total</th>
                  <th className="px-2.5 py-2 text-right text-[10px] uppercase text-slate-600">Pago</th>
                  <th className="px-2.5 py-2 text-right text-[10px] uppercase text-slate-600">Saldo</th>
                  <th className="px-2.5 py-2 text-center text-[10px] uppercase text-slate-600">Status</th>
                  <th className="px-2.5 py-2 text-left text-[10px] uppercase text-slate-600">Data pag.</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {data.linhas.map(l => (
                  <tr key={l.prestador_id + (l.local ?? "")} className="border-b border-slate-200">
                    <td className="px-2.5 py-2 text-slate-700">{formatCompetenciaCurta(l.competencia)}</td>
                    <td className="px-2.5 py-2 font-semibold text-slate-900">{l.prestador_nome}</td>
                    <td className="px-2.5 py-2 text-slate-600 text-[11px]">{l.local ?? "—"}</td>
                    <td className="px-2.5 py-2 text-right">{formatBRL(l.total)}</td>
                    <td className="px-2.5 py-2 text-right text-slate-500">{formatBRL(l.total_pago)}</td>
                    <td className="px-2.5 py-2 text-right font-semibold">{formatBRL(l.saldo)}</td>
                    <td className="px-2.5 py-2 text-center">
                      <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full ${STATUS_STYLE[l.status]}`}>
                        {l.status[0] + l.status.slice(1).toLowerCase()}
                      </span>
                    </td>
                    <td className="px-2.5 py-2 text-slate-600">{l.data_pagamento ? formatDataBR(l.data_pagamento) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === "dados" && (
        <EditorDadosContrato contratoId={data.contrato_id} inicial={data.dados_extras} onSaved={onSavedExtras} />
      )}
    </div>
  )
}

function formatCompetenciaCurta(comp: string): string {
  const [y, m] = comp.split("-")
  return `${m}.${y.slice(2)}`
}

function formatDataBR(s: string): string {
  // "2026-04-10" → "10/04/26"
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y.slice(2)}`
}
```

- [ ] **Step 3: Rodar build**

```bash
cd ~/spm-sistemafinanceiro/frontend && npm run build 2>&1 | tail -15
```

Expected: build OK.

- [ ] **Step 4: Commit**

```bash
cd ~/spm-sistemafinanceiro
git add frontend/components/contratos/editor-dados-contrato.tsx "frontend/app/(authed)/contratos/[id]/[competencia]/page.tsx"
git commit -m "feat(frontend): tela detalhe contrato com tabs + editor de dados extras"
```

---

## Task 7: Deploy via snapshot-temp + smoke prod

**Files:** nenhum do código — operacional.

- [ ] **Step 1: Criar repo snapshot temporário**

```bash
rm -rf /tmp/spm-deploy-temp
cd /tmp && git clone --depth 1 --branch main ~/spm-sistemafinanceiro spm-deploy-temp
cd /tmp/spm-deploy-temp
rm -rf .git
git init -b main -q
git add -A
git -c user.email='deploy@spm.local' -c user.name='SPM Deploy' commit -q -m 'Snapshot Track C deploy'
gh repo create drdamasceno/spm-deploy-temp-c --public --source=. --push --description "Temp snapshot Track C"
```

- [ ] **Step 2: Apontar os 2 services Render pro novo repo**

```bash
set -a; source ~/secrets/spm-deploy.env; set +a
for SID in srv-d7jspa3eo5us738efu9g srv-d7jspb1j2pic73clp0v0; do
  curl -s -X PATCH "https://api.render.com/v1/services/$SID" \
    -H "Authorization: Bearer $RENDER_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"repo": "https://github.com/drdamasceno/spm-deploy-temp-c"}'
done
```

- [ ] **Step 3: Disparar deploys manuais**

```bash
for SID in srv-d7jspa3eo5us738efu9g srv-d7jspb1j2pic73clp0v0; do
  curl -s -X POST "https://api.render.com/v1/services/$SID/deploys" \
    -H "Authorization: Bearer $RENDER_API_KEY" \
    -H "Content-Type: application/json" -d '{}'
done
```

- [ ] **Step 4: Pollar até live**

```bash
for i in $(seq 1 30); do
  sleep 20
  for SID in srv-d7jspa3eo5us738efu9g srv-d7jspb1j2pic73clp0v0; do
    s=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" "https://api.render.com/v1/services/$SID/deploys?limit=1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['deploy']['status'] if d else 'none')")
    echo "$SID: $s"
  done
  both_live=$(for SID in srv-d7jspa3eo5us738efu9g srv-d7jspb1j2pic73clp0v0; do curl -s -H "Authorization: Bearer $RENDER_API_KEY" "https://api.render.com/v1/services/$SID/deploys?limit=1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['deploy']['status'] if d else 'none')"; done | sort -u)
  if [ "$both_live" = "live" ]; then
    echo "=== AMBOS LIVE ==="
    break
  fi
done
```

Expected: ambos `live` em ~2-5 min.

- [ ] **Step 5: Smoke prod — endpoints**

```bash
# Login necessário pra testar com auth — smoke sem auth:
curl -s -o /dev/null -w "/ → %{http_code}\n" https://spm-financeiro-api.onrender.com/
curl -s -o /dev/null -w "/contratos → %{http_code}\n" "https://spm-financeiro-api.onrender.com/contratos?competencia=2026-02"
curl -s -o /dev/null -w "/contratos/anteriores → %{http_code}\n" "https://spm-financeiro-api.onrender.com/contratos/anteriores?ate=2026-04"
```

Expected: `/` → 200, `/contratos` → 401 (sem auth), `/contratos/anteriores` → 401.

- [ ] **Step 6: Reportar a Hugo**

Mensagem tipo:
> "Deploy Track C concluído. Abre https://spm-financeiro-web.onrender.com/contratos com competência 2026-02 e valida:
> 1. Lista deve mostrar 15 contratos-cidade (não mais 115)
> 2. Header 'Competências anteriores em aberto' aparece; click expande
> 3. Click num contrato abre detalhe com tabs 'Pagamentos' / 'Dados do contrato'"

---

## Self-Review

**1. Spec coverage** — todos os items do spec cobertos:
- Modelo 1 contrato=1 (uf, cidade): ✅ Task 1 (schema) + Task 2 (parser)
- Migração β agregadora dos 115: ✅ Task 1 (Step 2, block de consolidação)
- Novos campos em `contrato`: ✅ Task 1
- `registro_pp.local_pp`: ✅ Task 1 + Task 2 Step 6
- Parser novo: ✅ Task 2
- Queries + endpoints: ✅ Task 3 (listar + anteriores + PATCH + detalhe)
- Motor de cálculo Total/Pago/Saldo/Status/Data Pagamento: ✅ Task 3 em cada endpoint
- UI lista + carry-over collapsible com 3 níveis de idade: ✅ Task 5
- UI detalhe com tabs + editor: ✅ Task 6
- Deploy snapshot-temp: ✅ Task 7

**2. Placeholder scan** — varredura:
- Zero "TBD", "TODO", "implement later"
- Todo código tem implementação concreta
- Testes têm assertions específicas
- Comandos curl completos com URL real

**3. Type consistency** — types frontend = schemas Pydantic. Nomes como `ContratoCidadeListItem`, `ContratoAnteriorItem`, `ContratoDetalheOut`, `PrestadorLinhaDetalhe`, `ContratoDadosExtras` consistentes entre backend Python e frontend TS.

Nada a ajustar inline — plano OK.
