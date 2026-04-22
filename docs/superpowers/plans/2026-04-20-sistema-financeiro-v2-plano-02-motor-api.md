# SPM Sistema Financeiro v2 — Plano 2 (Motor + API, M3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development para executar este plano task-by-task. Steps usam checkbox (`- [ ]`) para tracking.

**Goal:** Implementar motor de classificação de conciliação em 3 camadas (regra → similaridade → valor) e expor todos os fluxos do sistema v2 via endpoints REST FastAPI.

**Architecture:** Um novo módulo Python puro (`classificador_conciliacao.py`) com três funções stateless que retornam sugestões ranqueadas por confiança. Schemas Pydantic em `backend/api/schemas/` para os 7 recursos novos. Routers em `backend/api/routers/` expondo upload de artefatos, conciliação, CRUD de catálogos, lifecycle de adiantamento, visões agregadas. Todos os routers usam RLS já habilitada (tokens do Supabase). TDD rigoroso para o motor; integration tests para routers via TestClient do FastAPI contra Supabase real.

**Tech Stack:** Python 3.12 · FastAPI 0.115 · Pydantic 2 · supabase-py 2.9.1 · rapidfuzz 3.10 (similarity) · pdfplumber 0.11.4 (via parsers do P1) · pytest.

**Spec de referência:** `docs/superpowers/specs/2026-04-20-sistema-financeiro-v2-design.md` (§5.4 motor, §5.5 leituras, §4 modelo de dados)

**Pré-requisitos (Plano 1 completo):**
- Migrations 0007-0009 aplicadas no Supabase `mkxehqhikcuykaxnpxff`
- Seeds `empresa` (SPM, FD) + 48 `categoria_despesa`
- Parsers `orcamento_xlsx.py`, `extrato_unicred.py`, `extract_bank_account` em `extrato_bradesco.py`
- Requirements sincronizados no venv (pytest, pg8000, pyotp, pdfplumber, rapidfuzz)

---

## File Structure

### Novos arquivos

```
backend/
  src/
    classificador_conciliacao.py              # motor de classificação 3 camadas
    persistencia_parsers.py                   # glue: parsers -> DB (reusa parsers do P1)
  api/
    schemas/
      catalogos.py                            # EmpresaOut, ProjetoIn/Out, CategoriaOut
      orcamento.py                            # OrcamentoCreate/Out, OrcamentoLinhaOut, ResultadoUpload
      extrato.py                              # UploadExtratoResponse
      conciliacao.py                          # SugestaoOut, ConciliacaoCreate, ConciliacaoOut
      regra.py                                # RegraClassificacaoIn/Out
      adiantamento.py                         # AdiantamentoCompensarIn, AdiantamentoOut
      contrato_competencia.py                 # ContratoCompetenciaOut (DRE por contrato)
      dashboard.py                            # DashboardResponse (KPIs + séries)
    routers/
      catalogos.py                            # GET /empresas, /projetos, /categorias ; POST projeto
      orcamento.py                            # POST /orcamentos/upload ; POST /orcamentos ; PATCH validar ; POST replicar ; GET
      extratos.py                             # POST /extratos/unicred/upload ; POST /extratos/bradesco/upload
      conciliacao.py                          # GET /conciliacoes/sugestoes ; POST /conciliacoes ; DELETE /conciliacoes/{id}
      regra_classificacao.py                  # GET /regras ; PATCH ; DELETE (soft)
      adiantamento.py                         # POST /adiantamentos/{id}/compensar
      contratos_competencia.py                # GET /contratos/{id}/competencia/{yyyy-mm}
      dashboard.py                            # GET /dashboard?competencia=...
  tests/
    test_classificador.py                     # 3 camadas + cascata
    test_router_orcamento.py
    test_router_extratos.py
    test_router_conciliacao.py
    test_router_adiantamento.py
    test_router_dashboard.py
```

### Arquivos modificados

```
backend/
  api/main.py                                 # register dos 8 routers novos
  src/persistencia_parsers.py                 # conector parser->DB
```

### Responsabilidades

- `classificador_conciliacao.py`: 4 funções puras (`normalizar_titular`, `sugerir_por_regra`, `sugerir_por_similaridade`, `sugerir_por_valor`) + `sugerir_cascata(tx, linhas_abertas, regras)` que retorna lista ranqueada.
- `persistencia_parsers.py`: funções helper que recebem resultado dos parsers do P1 e fazem upsert em `orcamento_linha` / `transacao_bancaria`.
- Routers: thin layer — validação Pydantic → chama service/src → serializa resposta. Auth via dependency `get_current_user` já existente em `api/deps.py`.

---

## M3-A — Motor de Classificação (5 tasks)

### Task 3.1: Normalizador de titular

**Files:**
- Create: `backend/src/classificador_conciliacao.py`
- Create: `backend/tests/test_classificador.py`

- [ ] **Step 1: Escrever testes**

```python
# backend/tests/test_classificador.py
"""Testes do classificador de conciliação (3 camadas + cascata)."""
import pytest

from backend.src.classificador_conciliacao import normalizar_titular


def test_normalizar_remove_acento_upper_trim():
    assert normalizar_titular("  José da Silva  ") == "JOSE DA SILVA"
    assert normalizar_titular("COND. Duque Hall SL0706") == "COND. DUQUE HALL SL0706"


def test_normalizar_preserva_numeros_e_pontuacao_util():
    assert normalizar_titular("04.368.898/0001-06 COPEL-DIS") == "04.368.898/0001-06 COPEL-DIS"


def test_normalizar_str_vazia_ou_none():
    assert normalizar_titular("") == ""
    assert normalizar_titular(None) == ""


def test_normalizar_colapsa_espacos():
    assert normalizar_titular("COND   DUQUE   HALL") == "COND DUQUE HALL"
```

- [ ] **Step 2: Rodar — falha por módulo inexistente**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro && source backend/.venv/bin/activate && \
python -m pytest backend/tests/test_classificador.py::test_normalizar_remove_acento_upper_trim -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implementar**

```python
# backend/src/classificador_conciliacao.py
"""
Motor de classificação de conciliação extrato ↔ orçamento.

Três camadas em cascata, da mais forte para mais fraca:
  1. REGRA SALVA       — confiança 0.95+, titular matching direto
  2. SIMILARIDADE+VALOR — confiança 0.70-0.90, rapidfuzz + tolerância de valor
  3. VALOR ÚNICO        — confiança 0.30-0.60, última opção

Stateless, Python puro. Não toca no DB.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Optional


def normalizar_titular(s: Optional[str]) -> str:
    """
    Normaliza um titular PIX para comparação consistente.
    - NFD + strip acentos
    - upper
    - colapsa whitespace
    - trim
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s
```

- [ ] **Step 4: Rodar testes — passam**

```bash
python -m pytest backend/tests/test_classificador.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/classificador_conciliacao.py backend/tests/test_classificador.py
git commit -m "feat(motor): normalizar_titular — base do classificador

NFD + strip acentos + upper + colapsa whitespace. Base canonica de
comparacao entre titular_pix e razao_social ao longo das 3 camadas do
classificador."
```

---

### Task 3.2: Camada 1 — Match por regra salva

**Files:**
- Modify: `backend/src/classificador_conciliacao.py`
- Modify: `backend/tests/test_classificador.py`

- [ ] **Step 1: Adicionar dataclasses e testes**

```python
# Adicionar em backend/tests/test_classificador.py
from backend.src.classificador_conciliacao import (
    Sugestao,
    Transacao,
    LinhaOrcamento,
    Regra,
    sugerir_por_regra,
)


def test_sugerir_por_regra_match_direto():
    tx = Transacao(id="tx1", titular_pix="Condominio Duque Hall", valor=-581.82, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="CENTRO EMPRESARIAL DUQUE HALL SL0705", valor_previsto=580.46, saldo_pendente=580.46)
    regra = Regra(id="r1", titular_pix_padrao="CONDOMINIO DUQUE HALL", orcamento_linha_id="l1", confianca_base=0.95, ativa=True)

    sugs = sugerir_por_regra(tx, [linha], [regra])
    assert len(sugs) == 1
    assert sugs[0].orcamento_linha_id == "l1"
    assert sugs[0].origem == "REGRA"
    assert sugs[0].confianca >= 0.95


def test_sugerir_por_regra_ignora_inativa():
    tx = Transacao(id="tx1", titular_pix="Fornecedor X", valor=-100.0, data_movimento="2026-04-09", origem_banco="UNICRED")
    regra = Regra(id="r1", titular_pix_padrao="FORNECEDOR X", orcamento_linha_id="l1", confianca_base=0.95, ativa=False)
    assert sugerir_por_regra(tx, [], [regra]) == []


def test_sugerir_por_regra_sem_match():
    tx = Transacao(id="tx1", titular_pix="Outro Titular", valor=-100.0, data_movimento="2026-04-09", origem_banco="UNICRED")
    regra = Regra(id="r1", titular_pix_padrao="CONDOMINIO DUQUE HALL", orcamento_linha_id="l1", confianca_base=0.95, ativa=True)
    assert sugerir_por_regra(tx, [], [regra]) == []
```

- [ ] **Step 2: Rodar — falha por import inexistente**

Expected: `ImportError: cannot import name 'Sugestao'`.

- [ ] **Step 3: Implementar — adicionar ao final de `classificador_conciliacao.py`**

```python
@dataclass
class Transacao:
    id: str
    titular_pix: Optional[str]
    valor: float                # negativo = débito
    data_movimento: str         # YYYY-MM-DD
    origem_banco: str           # "UNICRED" | "BRADESCO"


@dataclass
class LinhaOrcamento:
    id: str
    titular_razao_social: str
    valor_previsto: float
    saldo_pendente: float       # valor_previsto - sum(conciliacao_orcamento.valor_aplicado)


@dataclass
class Regra:
    id: str
    titular_pix_padrao: str         # já normalizado
    orcamento_linha_id: Optional[str]
    confianca_base: float
    ativa: bool


@dataclass
class Sugestao:
    orcamento_linha_id: str
    confianca: float
    origem: str                     # "REGRA" | "SIMILARIDADE" | "VALOR"
    valor_aplicado: float           # quanto da transação casa com a linha


def sugerir_por_regra(
    transacao: Transacao,
    linhas_abertas: List[LinhaOrcamento],
    regras: Iterable[Regra],
) -> List[Sugestao]:
    """
    Camada 1: se existir regra ativa cujo titular_pix_padrao == normalizar(transacao.titular_pix),
    sugerir a orcamento_linha_id memorizada (se ainda estiver entre as abertas).
    """
    titular_norm = normalizar_titular(transacao.titular_pix)
    if not titular_norm:
        return []

    linhas_por_id = {l.id: l for l in linhas_abertas}
    out: List[Sugestao] = []
    for r in regras:
        if not r.ativa:
            continue
        if r.titular_pix_padrao != titular_norm:
            continue
        if not r.orcamento_linha_id or r.orcamento_linha_id not in linhas_por_id:
            continue
        linha = linhas_por_id[r.orcamento_linha_id]
        valor_aplicado = min(abs(transacao.valor), linha.saldo_pendente)
        out.append(Sugestao(
            orcamento_linha_id=r.orcamento_linha_id,
            confianca=r.confianca_base,
            origem="REGRA",
            valor_aplicado=valor_aplicado,
        ))
    return out
```

- [ ] **Step 4: Rodar testes — passam**

```bash
python -m pytest backend/tests/test_classificador.py -v
```

Expected: 7 passed (4 anteriores + 3 desta).

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(motor): camada 1 do classificador — match por regra salva

Regra ativa com titular_pix_padrao == normalizar(titular_pix) sugere a
orcamento_linha memorizada com confianca_base. Fracionamento tratado via
min(abs(valor_tx), saldo_pendente_linha)."
```

---

### Task 3.3: Camada 2 — Similaridade + Valor

**Files:**
- Modify: `backend/src/classificador_conciliacao.py`
- Modify: `backend/tests/test_classificador.py`

- [ ] **Step 1: Testes**

```python
def test_sugerir_por_similaridade_match_alto():
    tx = Transacao(id="tx1", titular_pix="COPEL-DIS", valor=-88.53, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL DISTRIBUICAO S.A.", valor_previsto=88.53, saldo_pendente=88.53)
    sugs = sugerir_por_similaridade(tx, [linha])
    assert len(sugs) == 1
    assert sugs[0].orcamento_linha_id == "l1"
    assert sugs[0].origem == "SIMILARIDADE"
    assert 0.70 <= sugs[0].confianca <= 0.95


def test_sugerir_por_similaridade_valor_divergente():
    tx = Transacao(id="tx1", titular_pix="COPEL-DIS", valor=-500.00, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL DISTRIBUICAO S.A.", valor_previsto=88.53, saldo_pendente=88.53)
    # valor diverge >2% → não sugere
    assert sugerir_por_similaridade(tx, [linha]) == []


def test_sugerir_por_similaridade_titular_diverge():
    tx = Transacao(id="tx1", titular_pix="MAGMA MATERIAIS", valor=-88.53, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL DISTRIBUICAO S.A.", valor_previsto=88.53, saldo_pendente=88.53)
    # nomes distintos → similarity baixa → não sugere
    assert sugerir_por_similaridade(tx, [linha]) == []
```

- [ ] **Step 2: Rodar — falha por função ausente**

- [ ] **Step 3: Implementar**

```python
from rapidfuzz import fuzz


def sugerir_por_similaridade(
    transacao: Transacao,
    linhas_abertas: List[LinhaOrcamento],
    threshold_nome: int = 75,
    tolerancia_valor_pct: float = 0.02,
) -> List[Sugestao]:
    """
    Camada 2: similaridade de nome (WRatio do rapidfuzz) + valor dentro de 2%.

    Usa WRatio (Weighted Ratio) porque casos reais têm hífens conectando palavras
    (ex: "COPEL-DIS" no Unicred vs "COPEL DISTRIBUICAO S.A." no XLSX). WRatio
    combina ratio/partial_ratio/token_set_ratio/token_sort_ratio e escolhe a
    melhor — robusto a essas variações. token_set_ratio falha pois "COPEL-DIS"
    vira 1 token único (hífen não separa em rapidfuzz).

    Confiança mapeada linearmente do threshold ao máximo:
      score 75 → confiança 0.70
      score 100 → confiança 0.90
    """
    titular_norm = normalizar_titular(transacao.titular_pix)
    if not titular_norm:
        return []
    valor_tx = abs(transacao.valor)
    if valor_tx <= 0:
        return []

    out: List[Sugestao] = []
    for linha in linhas_abertas:
        razao_norm = normalizar_titular(linha.titular_razao_social)
        if not razao_norm:
            continue
        score = fuzz.WRatio(titular_norm, razao_norm)
        if score < threshold_nome:
            continue
        if linha.saldo_pendente <= 0:
            continue
        diff_rel = abs(valor_tx - linha.saldo_pendente) / max(valor_tx, linha.saldo_pendente)
        if diff_rel > tolerancia_valor_pct:
            continue
        # mapeia score ∈ [threshold_nome, 100] -> confiança ∈ [0.70, 0.90]
        confianca = 0.70 + (score - threshold_nome) / (100 - threshold_nome) * 0.20
        out.append(Sugestao(
            orcamento_linha_id=linha.id,
            confianca=round(confianca, 2),
            origem="SIMILARIDADE",
            valor_aplicado=min(valor_tx, linha.saldo_pendente),
        ))
    out.sort(key=lambda s: -s.confianca)
    return out
```

- [ ] **Step 4: Testes passam (10 total)**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(motor): camada 2 do classificador — similaridade + valor

rapidfuzz token_set_ratio >= 75 + diff de valor <= 2%. Confianca mapeada
linearmente de 0.70 (score 75) a 0.90 (score 100)."
```

---

### Task 3.4: Camada 3 — Valor único no mês

**Files:**
- Modify: `backend/src/classificador_conciliacao.py`
- Modify: `backend/tests/test_classificador.py`

- [ ] **Step 1: Testes**

```python
def test_sugerir_por_valor_unico_match():
    tx = Transacao(id="tx1", titular_pix="UNKNOWN TITULAR", valor=-776.74, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL SL 2003", valor_previsto=776.74, saldo_pendente=776.74)
    outra = LinhaOrcamento(id="l2", titular_razao_social="CLARO", valor_previsto=244.18, saldo_pendente=244.18)
    sugs = sugerir_por_valor(tx, [linha, outra])
    assert len(sugs) == 1
    assert sugs[0].orcamento_linha_id == "l1"
    assert sugs[0].origem == "VALOR"
    assert 0.30 <= sugs[0].confianca <= 0.60


def test_sugerir_por_valor_multiplas_candidatas_descarta():
    tx = Transacao(id="tx1", titular_pix="X", valor=-100.0, data_movimento="2026-04-09", origem_banco="UNICRED")
    l1 = LinhaOrcamento(id="l1", titular_razao_social="A", valor_previsto=100.0, saldo_pendente=100.0)
    l2 = LinhaOrcamento(id="l2", titular_razao_social="B", valor_previsto=100.0, saldo_pendente=100.0)
    # 2 candidatas por valor — ambiguidade → não sugere
    assert sugerir_por_valor(tx, [l1, l2]) == []
```

- [ ] **Step 2: Rodar — falha**

- [ ] **Step 3: Implementar**

```python
def sugerir_por_valor(
    transacao: Transacao,
    linhas_abertas: List[LinhaOrcamento],
    tolerancia_centavos: float = 0.01,
) -> List[Sugestao]:
    """
    Camada 3: se exatamente 1 linha tem valor_previsto == |valor_tx| (±1 centavo), sugerir.
    Confiança fixa 0.45 (meio do range 0.30-0.60).
    """
    valor_tx = abs(transacao.valor)
    if valor_tx <= 0:
        return []
    candidatas = [
        l for l in linhas_abertas
        if l.saldo_pendente > 0 and abs(l.saldo_pendente - valor_tx) <= tolerancia_centavos
    ]
    if len(candidatas) != 1:
        return []
    linha = candidatas[0]
    return [Sugestao(
        orcamento_linha_id=linha.id,
        confianca=0.45,
        origem="VALOR",
        valor_aplicado=min(valor_tx, linha.saldo_pendente),
    )]
```

- [ ] **Step 4: Testes passam (12 total)**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(motor): camada 3 do classificador — valor unico no mes

Exatamente 1 linha com saldo_pendente == |valor_tx| (+-1c) sugere com
confianca 0.45. Ambiguidade (2+ candidatas) descarta — vai pra revisao manual."
```

---

### Task 3.5: Cascata integrada

**Files:**
- Modify: `backend/src/classificador_conciliacao.py`
- Modify: `backend/tests/test_classificador.py`

- [ ] **Step 1: Testes de cascata**

```python
def test_cascata_regra_vence():
    tx = Transacao(id="tx1", titular_pix="Condominio Duque Hall", valor=-581.82, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha_pela_regra = LinhaOrcamento(id="l1", titular_razao_social="CENTRO DUQUE HALL SL0705", valor_previsto=580.46, saldo_pendente=580.46)
    linha_pela_similaridade = LinhaOrcamento(id="l2", titular_razao_social="CENTRO DUQUE HALL SL0706", valor_previsto=581.82, saldo_pendente=581.82)
    regra = Regra(id="r1", titular_pix_padrao="CONDOMINIO DUQUE HALL", orcamento_linha_id="l1", confianca_base=0.95, ativa=True)

    sugs = sugerir_cascata(tx, [linha_pela_regra, linha_pela_similaridade], [regra])
    assert sugs[0].origem == "REGRA"  # vence mesmo com valor menos exato


def test_cascata_fallback_similaridade():
    tx = Transacao(id="tx1", titular_pix="COPEL-DIS", valor=-88.53, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL DISTRIBUICAO S.A.", valor_previsto=88.53, saldo_pendente=88.53)
    sugs = sugerir_cascata(tx, [linha], regras=[])
    assert len(sugs) == 1
    assert sugs[0].origem == "SIMILARIDADE"


def test_cascata_fallback_valor():
    tx = Transacao(id="tx1", titular_pix="UNKNOWN", valor=-776.74, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL SL 2003", valor_previsto=776.74, saldo_pendente=776.74)
    sugs = sugerir_cascata(tx, [linha], regras=[])
    assert len(sugs) == 1
    assert sugs[0].origem == "VALOR"


def test_cascata_sem_sugestao():
    tx = Transacao(id="tx1", titular_pix="UNKNOWN", valor=-999.99, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL", valor_previsto=100.0, saldo_pendente=100.0)
    assert sugerir_cascata(tx, [linha], regras=[]) == []
```

- [ ] **Step 2: Rodar — falha**

- [ ] **Step 3: Implementar**

```python
def sugerir_cascata(
    transacao: Transacao,
    linhas_abertas: List[LinhaOrcamento],
    regras: Iterable[Regra],
) -> List[Sugestao]:
    """
    Aplica as 3 camadas em cascata. Para assim que alguma camada produz resultado.
    Retorna lista ordenada por confiança desc (normalmente 0 ou 1 sugestão).
    """
    regras_list = list(regras)

    sugs = sugerir_por_regra(transacao, linhas_abertas, regras_list)
    if sugs:
        return sorted(sugs, key=lambda s: -s.confianca)

    sugs = sugerir_por_similaridade(transacao, linhas_abertas)
    if sugs:
        return sugs  # já ordenado

    sugs = sugerir_por_valor(transacao, linhas_abertas)
    return sugs
```

- [ ] **Step 4: Testes passam (16 total)**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(motor): sugerir_cascata — 3 camadas em prioridade

Camada 1 (regra) > camada 2 (similaridade) > camada 3 (valor). Para na
primeira camada que produz sugestao. Retorna ordenado por confianca."
```

---

## M3-B — Schemas Pydantic (1 task)

### Task 3.6: Schemas dos 7 recursos novos

**Files:**
- Create: `backend/api/schemas/catalogos.py`
- Create: `backend/api/schemas/orcamento.py`
- Create: `backend/api/schemas/extrato.py`
- Create: `backend/api/schemas/conciliacao.py`
- Create: `backend/api/schemas/regra.py`
- Create: `backend/api/schemas/adiantamento.py`
- Create: `backend/api/schemas/contrato_competencia.py`
- Create: `backend/api/schemas/dashboard.py`

- [ ] **Step 1: Escrever schemas**

```python
# backend/api/schemas/catalogos.py
from uuid import UUID
from pydantic import BaseModel


class EmpresaOut(BaseModel):
    id: UUID
    codigo: str
    razao_social: str
    cnpj: str | None = None
    ativa: bool


class CategoriaOut(BaseModel):
    id: UUID
    nome: str
    descricao: str | None = None


class ProjetoIn(BaseModel):
    codigo: str
    descricao: str | None = None
    empresa_id: UUID


class ProjetoOut(ProjetoIn):
    id: UUID
    ativo: bool
```

```python
# backend/api/schemas/orcamento.py
from datetime import date
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class OrcamentoCreate(BaseModel):
    empresa_id: UUID
    competencia: str = Field(pattern=r"^\d{4}-\d{2}$")


class OrcamentoOut(BaseModel):
    id: UUID
    empresa_id: UUID
    competencia: str
    status: str
    criado_em: str


class OrcamentoLinhaOut(BaseModel):
    id: UUID
    orcamento_id: UUID
    natureza: str
    categoria_id: Optional[UUID]
    projeto_id: Optional[UUID]
    titular_cpf_cnpj: Optional[str]
    titular_razao_social: str
    contrato_id: Optional[UUID]
    valor_previsto: float
    data_previsao: Optional[date]
    observacao: Optional[str]


class ResultadoUploadOrcamento(BaseModel):
    orcamento_id: UUID
    total_linhas_inseridas: int
    linhas_por_secao: dict[str, int]
    linhas_descartadas: int
    avisos: list[str]
```

```python
# backend/api/schemas/extrato.py
from uuid import UUID
from pydantic import BaseModel


class UploadExtratoResponse(BaseModel):
    conta_id: UUID
    origem_banco: str                       # "UNICRED" | "BRADESCO"
    total_transacoes_inseridas: int
    periodo_inicio: str
    periodo_fim: str
    saldo_final: float
```

```python
# backend/api/schemas/conciliacao.py
from uuid import UUID
from pydantic import BaseModel


class SugestaoOut(BaseModel):
    transacao_id: UUID
    orcamento_linha_id: UUID
    confianca: float
    origem: str
    valor_aplicado: float


class ConciliacaoCreate(BaseModel):
    transacao_id: UUID
    orcamento_linha_id: UUID
    valor_aplicado: float
    confianca: float | None = None
    origem: str                              # "REGRA" | "SIMILARIDADE" | "VALOR" | "MANUAL"


class ConciliacaoOut(BaseModel):
    id: UUID
    transacao_id: UUID
    orcamento_linha_id: UUID
    valor_aplicado: float
    confianca: float | None
    origem: str
    aprovada_em: str
```

```python
# backend/api/schemas/regra.py
from uuid import UUID
from pydantic import BaseModel


class RegraClassificacaoOut(BaseModel):
    id: UUID
    titular_pix_padrao: str
    orcamento_linha_id: UUID | None
    categoria_id: UUID | None
    projeto_id: UUID | None
    empresa_id: UUID | None
    confianca_base: float
    uso_count: int
    ativa: bool
    ultima_utilizacao: str | None


class RegraClassificacaoPatch(BaseModel):
    ativa: bool | None = None
    confianca_base: float | None = None
```

```python
# backend/api/schemas/adiantamento.py
from uuid import UUID
from pydantic import BaseModel


class AdiantamentoOut(BaseModel):
    id: UUID
    prestador_id: UUID
    valor_bruto_solicitado: float
    percentual_desconto: float
    valor_liquido_pago: float
    receita_financeira: float
    data_pagamento: str
    status: str
    compensado_em_registro_pp_id: UUID | None


class AdiantamentoCompensarIn(BaseModel):
    registro_pp_id: UUID
```

```python
# backend/api/schemas/contrato_competencia.py
from uuid import UUID
from pydantic import BaseModel


class PrestadorLinha(BaseModel):
    nome: str
    valor_pp: float
    valor_pago: float
    datas_pix: list[str]
    status: str                              # "PAGO" | "PARCIAL" | "PENDENTE"


class ContratoCompetenciaOut(BaseModel):
    contrato_id: UUID
    nome_contrato: str
    competencia: str
    total_devido: float
    total_pago: float
    percentual_pago: float
    receita_prevista: float | None
    margem_projetada: float | None
    prestadores: list[PrestadorLinha]
```

```python
# backend/api/schemas/dashboard.py
from pydantic import BaseModel


class KPIs(BaseModel):
    saldo_inicial: float
    saidas_mes: float
    previsto_a_pagar: float
    saldo_atual: float


class BarraPxR(BaseModel):
    categoria: str
    previsto: float
    realizado: float
    pct: float


class Alerta(BaseModel):
    tipo: str                                # "NAO_CONCILIADO" | "VENCIDO" | "PAGO_A_MAIOR" | "ESTORNO"
    mensagem: str
    ref_id: str | None
    ref_tipo: str | None


class DashboardResponse(BaseModel):
    competencia: str
    empresa_filtro: str                      # "SPM" | "FD" | "TODAS"
    kpis: KPIs
    saidas_por_natureza: dict[str, float]    # { "DESPESA_FIXA": 123.45, ... }
    previsto_x_realizado: list[BarraPxR]
    alertas: list[Alerta]
```

- [ ] **Step 2: Commit**

```bash
git add backend/api/schemas/
git commit -m "feat(schemas): 8 schemas Pydantic para os recursos do v2

catalogos (empresa/projeto/categoria), orcamento, extrato, conciliacao,
regra, adiantamento, contrato_competencia, dashboard."
```

---

## M3-C — Routers (8 tasks)

Para todos os routers: importar `get_current_user` e `get_supabase_authed` de `backend.api.deps`. Registrar no `backend.api.main` ao final de cada task.

### Task 3.7: Router catálogos (GET empresa/projeto/categoria + POST projeto)

**Files:**
- Create: `backend/api/routers/catalogos.py`
- Create: `backend/tests/test_router_catalogos.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: Teste integration**

```python
# backend/tests/test_router_catalogos.py
"""Testes de integração dos endpoints de catálogo (empresa/projeto/categoria)."""
import os
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SERVICE_ROLE_KEY não disponível",
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def ceo_headers():
    # Reusa fixture do test_rodada_aprovacao se existir; aqui helper mínimo.
    from backend.tests.conftest import ceo_headers as _h
    yield _h()  # ajustar se o fixture for diferente


def test_listar_empresas(client, ceo_headers):
    r = client.get("/empresas", headers=ceo_headers)
    assert r.status_code == 200
    data = r.json()
    codigos = {e["codigo"] for e in data}
    assert {"SPM", "FD"}.issubset(codigos)


def test_listar_categorias_nao_vazio(client, ceo_headers):
    r = client.get("/categorias", headers=ceo_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 40


def test_criar_projeto_e_listar(client, ceo_headers):
    # Pega empresa SPM
    r = client.get("/empresas", headers=ceo_headers)
    spm = next(e for e in r.json() if e["codigo"] == "SPM")
    # Cria projeto
    payload = {"codigo": "TEST-R37-PROJ", "descricao": "Teste router catálogos", "empresa_id": spm["id"]}
    r = client.post("/projetos", headers=ceo_headers, json=payload)
    assert r.status_code == 201
    proj = r.json()
    assert proj["codigo"] == "TEST-R37-PROJ"
    # Lista projetos
    r = client.get("/projetos", headers=ceo_headers)
    assert any(p["codigo"] == "TEST-R37-PROJ" for p in r.json())
    # Cleanup
    client.delete(f"/projetos/{proj['id']}", headers=ceo_headers)
```

- [ ] **Step 2: Rodar — falha**

- [ ] **Step 3: Router**

```python
# backend/api/routers/catalogos.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.catalogos import EmpresaOut, CategoriaOut, ProjetoIn, ProjetoOut


router = APIRouter()


@router.get("/empresas", response_model=List[EmpresaOut])
def listar_empresas(current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    r = client.table("empresa").select("*").eq("ativa", True).order("codigo").execute()
    return r.data


@router.get("/categorias", response_model=List[CategoriaOut])
def listar_categorias(current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    r = client.table("categoria_despesa").select("*").order("nome").execute()
    return r.data


@router.get("/projetos", response_model=List[ProjetoOut])
def listar_projetos(current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    r = client.table("projeto").select("*").eq("ativo", True).order("codigo").execute()
    return r.data


@router.post("/projetos", response_model=ProjetoOut, status_code=status.HTTP_201_CREATED)
def criar_projeto(payload: ProjetoIn, current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    r = client.table("projeto").insert(payload.model_dump(mode="json")).execute()
    if not r.data:
        raise HTTPException(status_code=400, detail={"error": "Falha ao criar projeto"})
    return r.data[0]


@router.delete("/projetos/{projeto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_projeto(projeto_id: UUID, current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    client.table("projeto").delete().eq("id", str(projeto_id)).execute()
    return None
```

- [ ] **Step 4: Registrar no main**

Abrir `backend/api/main.py` e adicionar:
```python
from backend.api.routers import catalogos
app.include_router(catalogos.router, tags=["catalogos"])
```

- [ ] **Step 5: Testes passam**

```bash
python -m pytest backend/tests/test_router_catalogos.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/api/routers/catalogos.py backend/api/main.py backend/tests/test_router_catalogos.py
git commit -m "feat(api): router catalogos — GET empresas/categorias/projetos + POST/DELETE projeto"
```

---

### Task 3.8: Router orçamento — upload + CRUD cabeçalho + replicação

**Files:**
- Create: `backend/src/persistencia_parsers.py`
- Create: `backend/api/routers/orcamento.py`
- Create: `backend/tests/test_router_orcamento.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: Teste upload do XLSX real**

```python
# backend/tests/test_router_orcamento.py
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SERVICE_ROLE_KEY ausente",
)

FIXTURE = Path(__file__).parent / "fixtures" / "SPM_Orcamento_04_2026.xlsx"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def ceo_headers():
    from backend.tests.conftest import ceo_headers as _h
    return _h()


def test_upload_orcamento_cria_linhas(client, ceo_headers, request):
    # Pega empresa SPM
    r = client.get("/empresas", headers=ceo_headers)
    spm_id = next(e["id"] for e in r.json() if e["codigo"] == "SPM")
    with open(FIXTURE, "rb") as f:
        r = client.post(
            "/orcamentos/upload",
            headers=ceo_headers,
            data={"empresa_id": spm_id, "competencia": "2099-11"},
            files={"arquivo": ("orcamento.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["total_linhas_inseridas"] > 100
    assert data["linhas_por_secao"]["DESPESA_FIXA"] > 30
    # Cleanup
    orcamento_id = data["orcamento_id"]
    request.addfinalizer(lambda: client.delete(f"/orcamentos/{orcamento_id}", headers=ceo_headers))


def test_upload_orcamento_duplicado_rejeita(client, ceo_headers):
    r = client.get("/empresas", headers=ceo_headers)
    spm_id = next(e["id"] for e in r.json() if e["codigo"] == "SPM")
    # 1o upload cria 2099-10
    with open(FIXTURE, "rb") as f:
        client.post("/orcamentos/upload", headers=ceo_headers,
                    data={"empresa_id": spm_id, "competencia": "2099-10"},
                    files={"arquivo": ("o.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    # 2o upload mesma competência falha (UNIQUE)
    with open(FIXTURE, "rb") as f:
        r = client.post("/orcamentos/upload", headers=ceo_headers,
                        data={"empresa_id": spm_id, "competencia": "2099-10"},
                        files={"arquivo": ("o.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 409
    # Cleanup
    resp_orcamento = client.get(f"/orcamentos?empresa_id={spm_id}&competencia=2099-10", headers=ceo_headers)
    if resp_orcamento.status_code == 200 and resp_orcamento.json():
        client.delete(f"/orcamentos/{resp_orcamento.json()[0]['id']}", headers=ceo_headers)
```

- [ ] **Step 2: Rodar — falha**

- [ ] **Step 3: Implementar persistência**

```python
# backend/src/persistencia_parsers.py
"""Glue entre parsers (Python puro) e Supabase (persistência)."""
from typing import Dict, List
from uuid import UUID
from supabase import Client

from backend.src.orcamento_xlsx import OrcamentoParser, OrcamentoLinhaParsed, NaturezaOrcamento


def persistir_orcamento_xlsx(
    client: Client,
    arquivo_bytes: bytes,
    empresa_id: UUID,
    competencia: str,
    criado_por: UUID,
) -> Dict:
    """
    Parsea XLSX e insere orcamento + orcamento_linha em transação lógica.
    Retorna dict no formato ResultadoUploadOrcamento.

    Raises:
        ValueError: se já existir orcamento para (empresa, competencia).
    """
    resultado = OrcamentoParser().parse_completo(arquivo_bytes)

    # Cria cabeçalho
    ins = client.table("orcamento").insert({
        "empresa_id": str(empresa_id),
        "competencia": competencia,
        "status": "RASCUNHO",
        "criado_por": str(criado_por),
    }).execute()
    if not ins.data:
        raise ValueError("Falha ao criar orcamento (possível duplicata)")
    orcamento_id = ins.data[0]["id"]

    # Lookup de catálogos: categoria_despesa e projeto
    cats = client.table("categoria_despesa").select("id,nome").execute()
    mapa_categoria = {c["nome"].upper(): c["id"] for c in cats.data}
    projs = client.table("projeto").select("id,codigo").execute()
    mapa_projeto = {p["codigo"].upper(): p["id"] for p in projs.data}
    empresa_by_codigo = {
        e["codigo"]: e["id"]
        for e in client.table("empresa").select("id,codigo").execute().data
    }

    rows_para_inserir = []
    avisos: List[str] = []
    for linha in resultado.linhas:
        cat_id = mapa_categoria.get((linha.categoria or "").upper())
        proj_id = mapa_projeto.get((linha.projeto or "").upper())
        emp_id = empresa_by_codigo.get(linha.empresa_codigo, str(empresa_id))
        if linha.projeto and not proj_id:
            avisos.append(f"Projeto '{linha.projeto}' (linha XLSX {linha.linha_xlsx}) não cadastrado — campo ficou NULL.")
        rows_para_inserir.append({
            "orcamento_id": orcamento_id,
            "natureza": linha.natureza.value,
            "categoria_id": cat_id,
            "projeto_id": proj_id,
            "titular_cpf_cnpj": linha.titular_cpf_cnpj,
            "titular_razao_social": linha.titular_razao_social,
            "valor_previsto": linha.valor_previsto,
            "data_previsao": linha.data_previsao,
            "observacao": linha.observacao,
        })

    # Bulk insert
    if rows_para_inserir:
        client.table("orcamento_linha").insert(rows_para_inserir).execute()

    return {
        "orcamento_id": orcamento_id,
        "total_linhas_inseridas": len(rows_para_inserir),
        "linhas_por_secao": {k.value: v for k, v in resultado.linhas_por_secao.items()},
        "linhas_descartadas": resultado.linhas_descartadas,
        "avisos": avisos,
    }
```

- [ ] **Step 4: Router**

```python
# backend/api/routers/orcamento.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.orcamento import (
    OrcamentoCreate, OrcamentoOut, OrcamentoLinhaOut, ResultadoUploadOrcamento,
)
from backend.src.persistencia_parsers import persistir_orcamento_xlsx


router = APIRouter(prefix="/orcamentos", tags=["orcamento"])


@router.get("", response_model=List[OrcamentoOut])
def listar(empresa_id: UUID | None = None, competencia: str | None = None, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    q = client.table("orcamento").select("*")
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    if competencia:
        q = q.eq("competencia", competencia)
    return q.order("competencia", desc=True).execute().data


@router.post("", response_model=OrcamentoOut, status_code=status.HTTP_201_CREATED)
def criar(payload: OrcamentoCreate, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    try:
        r = client.table("orcamento").insert({
            **payload.model_dump(mode="json"),
            "status": "RASCUNHO",
            "criado_por": current["id"],
        }).execute()
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(409, detail={"error": "Orcamento ja existe para essa (empresa, competencia)"})
        raise
    return r.data[0]


@router.post("/upload", response_model=ResultadoUploadOrcamento, status_code=status.HTTP_201_CREATED)
def upload(
    empresa_id: UUID = Form(...),
    competencia: str = Form(..., pattern=r"^\d{4}-\d{2}$"),
    arquivo: UploadFile = File(...),
    current=Depends(get_current_user),
):
    client = get_supabase_authed(current["jwt"])
    bytes_xlsx = arquivo.file.read()
    try:
        return persistir_orcamento_xlsx(client, bytes_xlsx, empresa_id, competencia, current["id"])
    except ValueError as e:
        raise HTTPException(409, detail={"error": str(e)})


@router.patch("/{orcamento_id}/validar", response_model=OrcamentoOut)
def validar(orcamento_id: UUID, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    r = client.table("orcamento").update({
        "status": "VALIDADO",
        "validado_em": "now()",
    }).eq("id", str(orcamento_id)).execute()
    if not r.data:
        raise HTTPException(404)
    return r.data[0]


@router.post("/{orcamento_id}/replicar", response_model=OrcamentoOut)
def replicar(orcamento_id: UUID, nova_competencia: str, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    # Busca orçamento origem
    origem = client.table("orcamento").select("*").eq("id", str(orcamento_id)).single().execute().data
    if not origem:
        raise HTTPException(404)
    # Cria novo
    novo = client.table("orcamento").insert({
        "empresa_id": origem["empresa_id"],
        "competencia": nova_competencia,
        "status": "RASCUNHO",
        "criado_por": current["id"],
    }).execute()
    novo_id = novo.data[0]["id"]
    # Copia linhas
    linhas = client.table("orcamento_linha").select("*").eq("orcamento_id", str(orcamento_id)).execute().data
    if linhas:
        rows = [{**l, "orcamento_id": novo_id, "id": None, "created_at": None} for l in linhas]
        for r in rows:
            r.pop("id", None)
            r.pop("created_at", None)
        client.table("orcamento_linha").insert(rows).execute()
    return novo.data[0]


@router.delete("/{orcamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(orcamento_id: UUID, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    client.table("orcamento").delete().eq("id", str(orcamento_id)).execute()
    return None
```

- [ ] **Step 5: Registrar no main**

```python
from backend.api.routers import orcamento
app.include_router(orcamento.router)
```

- [ ] **Step 6: Testes passam, commit**

```bash
git add backend/src/persistencia_parsers.py backend/api/routers/orcamento.py backend/tests/test_router_orcamento.py backend/api/main.py
git commit -m "feat(api): router orcamento — upload XLSX (6 secoes) + CRUD + replicacao"
```

---

### Task 3.9: Router extratos — upload Unicred PDF + Bradesco OFX

**Files:**
- Create: `backend/api/routers/extratos.py`
- Create: `backend/tests/test_router_extratos.py`
- Modify: `backend/src/persistencia_parsers.py` (adicionar 2 funções)
- Modify: `backend/api/main.py`

- [ ] **Step 1: Adicionar ao `persistencia_parsers.py`**

```python
from backend.src.extrato_unicred import UnicredParser
from backend.src.extrato_bradesco import extract_bank_account, parse_ofx   # função existente do parser


def persistir_extrato_unicred(client, arquivo_bytes: bytes, conta_id: UUID) -> dict:
    parser = UnicredParser()
    meta = parser.extrair_metadados(arquivo_bytes)
    transacoes = parser.parse(arquivo_bytes)
    rows = [{
        "conta_id": str(conta_id),
        "valor": t.valor,
        "data_extrato": t.data_movimento,
        "mes_competencia": t.data_movimento[:7],
        "tipo": "CREDITO" if t.valor > 0 else "DEBITO",
        "status_conciliacao": "NAO_CLASSIFICADO",
        "descricao": t.historico[:500],
        "titular_pix": t.titular_pix,
        "origem_banco": "UNICRED",
        "natureza_lancamento": t.natureza.value,
    } for t in transacoes]
    if rows:
        client.table("transacao_bancaria").insert(rows).execute()
    return {
        "conta_id": conta_id,
        "origem_banco": "UNICRED",
        "total_transacoes_inseridas": len(rows),
        "periodo_inicio": meta.periodo_inicio,
        "periodo_fim": meta.periodo_fim,
        "saldo_final": meta.saldo_final,
    }


def persistir_extrato_bradesco(client, arquivo_bytes: bytes) -> dict:
    """Rota pelo BANKID+ACCTID para resolver conta_id."""
    bankid, acctid = extract_bank_account(arquivo_bytes)
    conta = client.table("conta_bancaria").select("id,finalidade").eq("banco", bankid).eq("conta", acctid).single().execute()
    if not conta.data:
        raise ValueError(f"Conta nao cadastrada: banco {bankid} conta {acctid}")
    # Parse via parser existente — reutilize função de parse_ofx se disponível, ou chame motor atual.
    # Para simplificar, aqui delegamos à função existente do projeto.
    transacoes = parse_ofx(arquivo_bytes)
    # ... inserir ...
    # (Esta parte depende do parser existente — validar assinatura antes de executar.)
    raise NotImplementedError("Implementar após validar assinatura de parse_ofx existente.")
```

**Atenção:** a linha `parse_ofx` precisa ser validada no `extrato_bradesco.py` existente. Se não houver função com esse nome, o subagent deve ler o arquivo e usar a função correspondente (provavelmente `parse_extrato_ofx` ou similar). Ajustar antes de rodar testes.

- [ ] **Step 2: Router**

```python
# backend/api/routers/extratos.py
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.extrato import UploadExtratoResponse
from backend.src.persistencia_parsers import persistir_extrato_unicred, persistir_extrato_bradesco


router = APIRouter(prefix="/extratos", tags=["extratos"])


@router.post("/unicred/upload", response_model=UploadExtratoResponse, status_code=status.HTTP_201_CREATED)
def upload_unicred(
    conta_id: UUID = Form(...),
    arquivo: UploadFile = File(...),
    current=Depends(get_current_user),
):
    client = get_supabase_authed(current["jwt"])
    pdf_bytes = arquivo.file.read()
    return persistir_extrato_unicred(client, pdf_bytes, conta_id)


@router.post("/bradesco/upload", response_model=UploadExtratoResponse, status_code=status.HTTP_201_CREATED)
def upload_bradesco(
    arquivo: UploadFile = File(...),
    current=Depends(get_current_user),
):
    client = get_supabase_authed(current["jwt"])
    ofx_bytes = arquivo.file.read()
    try:
        return persistir_extrato_bradesco(client, ofx_bytes)
    except ValueError as e:
        raise HTTPException(400, detail={"error": str(e)})
```

- [ ] **Step 3: Registrar no main, teste, commit**

```bash
git commit -m "feat(api): router extratos — upload Unicred PDF + Bradesco OFX (routing BANKID/ACCTID)"
```

---

### Task 3.10: Router conciliacao — GET sugestoes + POST aplicar + DELETE desfazer

**Files:**
- Create: `backend/api/routers/conciliacao.py`
- Create: `backend/tests/test_router_conciliacao.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: Implementar**

```python
# backend/api/routers/conciliacao.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.conciliacao import SugestaoOut, ConciliacaoCreate, ConciliacaoOut
from backend.src.classificador_conciliacao import (
    sugerir_cascata, normalizar_titular, Transacao, LinhaOrcamento, Regra,
)


router = APIRouter(prefix="/conciliacoes", tags=["conciliacao"])


def _carregar_contexto(client, orcamento_id: UUID, conta_id: UUID | None):
    """Carrega linhas abertas do orcamento, transações não conciliadas da conta, regras ativas."""
    # Linhas abertas: valor_previsto > sum(conciliacao_orcamento.valor_aplicado)
    linhas = client.table("orcamento_linha").select("*").eq("orcamento_id", str(orcamento_id)).execute().data
    conc = client.table("conciliacao_orcamento").select("orcamento_linha_id,valor_aplicado").execute().data
    sums = {}
    for c in conc:
        sums[c["orcamento_linha_id"]] = sums.get(c["orcamento_linha_id"], 0) + c["valor_aplicado"]
    abertas = []
    for l in linhas:
        aplicado = sums.get(l["id"], 0)
        saldo = float(l["valor_previsto"]) - aplicado
        if saldo > 0.005:
            abertas.append(LinhaOrcamento(
                id=l["id"],
                titular_razao_social=l["titular_razao_social"],
                valor_previsto=float(l["valor_previsto"]),
                saldo_pendente=saldo,
            ))

    q = client.table("transacao_bancaria").select("*").eq("status_conciliacao", "NAO_CLASSIFICADO")
    if conta_id:
        q = q.eq("conta_id", str(conta_id))
    txs_raw = q.execute().data
    txs = [Transacao(
        id=t["id"],
        titular_pix=t.get("titular_pix"),
        valor=float(t["valor"]),
        data_movimento=str(t["data_extrato"]),
        origem_banco=t.get("origem_banco", "BRADESCO"),
    ) for t in txs_raw]

    regras_raw = client.table("regra_classificacao").select("*").eq("ativa", True).execute().data
    regras = [Regra(
        id=r["id"],
        titular_pix_padrao=r["titular_pix_padrao"],
        orcamento_linha_id=r["orcamento_linha_id"],
        confianca_base=float(r["confianca_base"]),
        ativa=r["ativa"],
    ) for r in regras_raw]

    return txs, abertas, regras


@router.get("/sugestoes", response_model=List[SugestaoOut])
def sugestoes(orcamento_id: UUID, conta_id: UUID | None = None, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    txs, abertas, regras = _carregar_contexto(client, orcamento_id, conta_id)
    out = []
    for tx in txs:
        for s in sugerir_cascata(tx, abertas, regras):
            out.append(SugestaoOut(
                transacao_id=tx.id,
                orcamento_linha_id=s.orcamento_linha_id,
                confianca=s.confianca,
                origem=s.origem,
                valor_aplicado=s.valor_aplicado,
            ))
    return out


@router.post("", response_model=ConciliacaoCreate, status_code=status.HTTP_201_CREATED)
def criar_conciliacao(payload: ConciliacaoCreate, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    # 1. Insere conciliacao
    ins = client.table("conciliacao_orcamento").insert({
        "transacao_id": str(payload.transacao_id),
        "orcamento_linha_id": str(payload.orcamento_linha_id),
        "valor_aplicado": payload.valor_aplicado,
        "confianca": payload.confianca,
        "origem": payload.origem,
        "aprovada_por": current["id"],
    }).execute()
    if not ins.data:
        raise HTTPException(400, detail={"error": "Falha ao criar conciliacao"})

    # 2. Atualiza transacao_bancaria
    client.table("transacao_bancaria").update({
        "status_conciliacao": "MATCH_AUTOMATICO" if payload.origem in ("REGRA","SIMILARIDADE","VALOR") else "MATCH_AUTOMATICO",
    }).eq("id", str(payload.transacao_id)).execute()

    # 3. Se não veio de regra, cria/atualiza regra_classificacao para o futuro
    if payload.origem != "REGRA":
        tx = client.table("transacao_bancaria").select("titular_pix").eq("id", str(payload.transacao_id)).single().execute().data
        if tx and tx.get("titular_pix"):
            titular_norm = normalizar_titular(tx["titular_pix"])
            if titular_norm:
                # upsert: desativa regra existente com mesmo titular (se houver) e cria nova
                client.table("regra_classificacao").update({"ativa": False}).eq("titular_pix_padrao", titular_norm).eq("ativa", True).execute()
                client.table("regra_classificacao").insert({
                    "titular_pix_padrao": titular_norm,
                    "orcamento_linha_id": str(payload.orcamento_linha_id),
                    "confianca_base": 0.95,
                    "ativa": True,
                    "criada_por": current["id"],
                }).execute()

    return payload


@router.delete("/{conciliacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(conciliacao_id: UUID, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    # Busca antes pra saber a transação
    c = client.table("conciliacao_orcamento").select("transacao_id").eq("id", str(conciliacao_id)).single().execute().data
    if c:
        # Apaga conciliacao
        client.table("conciliacao_orcamento").delete().eq("id", str(conciliacao_id)).execute()
        # Volta transação pra NAO_CLASSIFICADO se não sobrar outra conciliacao dela
        outras = client.table("conciliacao_orcamento").select("id").eq("transacao_id", c["transacao_id"]).execute().data
        if not outras:
            client.table("transacao_bancaria").update({"status_conciliacao": "NAO_CLASSIFICADO"}).eq("id", c["transacao_id"]).execute()
    return None
```

- [ ] **Step 2: Teste (integração mínima com TestClient)**

Validar end-to-end: sobe orçamento, sobe extrato Unicred, chama `/conciliacoes/sugestoes`, confirma que retorna ≥1 sugestão de camada SIMILARIDADE (ex: COPEL → COPEL DISTRIBUICAO), aplica via POST, confirma que cria regra_classificacao, chama sugestões de novo e vê que agora é camada REGRA.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(api): router conciliacao — sugestoes cascata + aplicar + desfazer + aprendizado de regra"
```

---

### Task 3.11: Router regra_classificacao — listar, editar, desativar

**Files:**
- Create: `backend/api/routers/regra_classificacao.py`
- Modify: `backend/api/main.py`

- [ ] Implementar endpoints `GET /regras`, `PATCH /regras/{id}`, `DELETE /regras/{id}` (soft delete = `ativa=false`).
- Segue padrão dos outros routers.
- Testes simples: criar via conciliacao (Task 3.10), listar, desativar.
- Commit: `feat(api): router regra_classificacao — listar/editar/desativar`

---

### Task 3.12: Router adiantamento — compensar contra PP

**Files:**
- Create: `backend/api/routers/adiantamento.py`
- Modify: `backend/api/main.py`

- [ ] Endpoint `POST /adiantamentos/{id}/compensar` com body `{"registro_pp_id": UUID}`.
- Implementação:
  1. Valida que `adiantamento.status = 'ABERTO'`
  2. Valida que `registro_pp.prestador_id = adiantamento.prestador_id`
  3. Update: `status='COMPENSADO_TOTAL'`, `compensado_em_registro_pp_id=<id>`, `compensado_em=now()`
- Testes: criar adiantamento fake, criar registro_pp do mesmo prestador, chamar endpoint, confirmar lifecycle.
- Commit: `feat(api): router adiantamento — POST compensar (lifecycle manual)`

---

### Task 3.13: Router contrato × competência — DRE por contrato

**Files:**
- Create: `backend/api/routers/contratos_competencia.py`
- Modify: `backend/api/main.py`

- [ ] Endpoint `GET /contratos/{contrato_id}/competencia/{yyyy-mm}` que retorna `ContratoCompetenciaOut`.

```python
@router.get("/contratos/{contrato_id}/competencia/{competencia}", response_model=ContratoCompetenciaOut)
def view(contrato_id: UUID, competencia: str, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    # 1. Contrato
    ctt = client.table("contrato").select("*").eq("id", str(contrato_id)).single().execute().data
    # 2. registro_pp da competência
    rpps = client.table("registro_pp").select(
        "id,prestador_id,saldo_pp,prestador(nome)"
    ).eq("contrato_id", str(contrato_id)).eq("mes_competencia", competencia).execute().data
    # 3. transações matched
    for rp in rpps:
        txs = client.table("transacao_bancaria").select("valor,data_extrato").eq(
            "registro_pp_id", rp["id"]
        ).execute().data
        rp["valor_pago"] = sum(abs(float(t["valor"])) for t in txs)
        rp["datas_pix"] = [str(t["data_extrato"]) for t in txs]
    # 4. Agrega + busca orcamento_linha DESPESA_PROFISSIONAIS do contrato+competencia
    # (seguir lógica documentada no spec §5.5)
    ...
```

Retornar DRE com prestadores + totais + margem projetada (se receita_prevista conhecida).

- Commit: `feat(api): router contratos_competencia — DRE por contrato (PP + orcamento)`

---

### Task 3.14: Router dashboard + registro final no main

**Files:**
- Create: `backend/api/routers/dashboard.py`
- Modify: `backend/api/main.py`
- Create: `backend/tests/test_smoke_e2e.py`

- [ ] Endpoint `GET /dashboard?competencia=YYYY-MM&empresa=SPM|FD|TODAS` que retorna `DashboardResponse`.
- Agregações SQL documentadas no spec §5.5. Implementar como múltiplas queries via supabase-py (JOIN no Postgres via `.select("*,fk(*)")`).
- KPIs:
  - saldo_inicial: saldo atual de todas contas no início do mês (precisa materializar — ou usar saldo_anterior do primeiro extrato do mês + soma até a data limite)
  - saidas_mes: SUM(transacao_bancaria.valor) WHERE tipo=DEBITO AND mes_competencia=? (filtra fora TRANSFERENCIA_INTERNA)
  - previsto_a_pagar: SUM(orcamento_linha.valor_previsto) do orcamento da competência
  - saldo_atual: saldo_inicial + sum(creditos) - sum(debitos)

- Alertas: queries separadas (transações sem conciliação há > 5 dias; orcamento_linha com data_previsao < hoje e saldo > 0; etc.)

- Smoke test e2e: upload orçamento + extrato → sugestões → conciliação → dashboard → confirma KPIs coerentes.

- [ ] Commit: `feat(api): router dashboard + smoke test e2e — fecha M3 do spec v2`

---

## Self-review

Ao fim do Plano 2, rodar:

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro && source backend/.venv/bin/activate && \
python -m pytest backend/tests/ -v --tb=short
```

Expected:
- Todos os testes do Plano 1 (20+ do motor/parsers) continuam passando — sem regressão
- Novos testes do motor de classificação (~16 testes)
- Novos testes de routers (ao menos 1 smoke por router × 8 routers = 8+)
- Total ≥ 50 passed

Executar smoke manual:
1. Cadastrar conta Unicred via SQL direto (conta `6688055`, banco `UNICRED`, finalidade `FIXAS`).
2. `curl -X POST /orcamentos/upload` com XLSX fixture.
3. `curl -X POST /extratos/unicred/upload` com PDF fixture.
4. `curl /conciliacoes/sugestoes?orcamento_id=...` — confirma ≥ 20 sugestões.
5. `curl -X POST /conciliacoes` para aplicar uma sugestão — confirma criação de regra.
6. `curl /dashboard?competencia=2099-11` — confirma KPIs.

Commit final do marco:

```bash
git commit --allow-empty -m "chore: encerra Plano 2 (Motor + API) do Sistema Financeiro v2

M3 do spec completo. Próximo: Plano 3 (UI + Go Live)."
```

## Checklist de entrega (Plano 2)

- [x] 5 tasks de motor (normalizar + camada 1 + camada 2 + camada 3 + cascata) — 16 testes
- [x] 1 task de schemas Pydantic — 8 arquivos
- [x] 8 tasks de routers (catálogos, orçamento, extratos, conciliação, regra, adiantamento, contrato×competência, dashboard)
- [x] Smoke test e2e cobrindo o fluxo completo
- [x] Motor aprende regra automaticamente ao aprovar conciliação não-REGRA
- [x] Nenhuma regressão nos testes do Plano 1

## Próximos passos

Plano 3 (M4+M5+M6): 7 telas Next.js + integração + deploy. Escrito após Plano 2 completo.
