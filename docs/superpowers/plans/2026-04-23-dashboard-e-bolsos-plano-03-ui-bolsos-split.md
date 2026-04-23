# Track B — Plano 03: UI de bolsos + split de transação (Fase D)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao Hugo a UI para classificar linhas de orçamento por bolso (SPM/FD/Hugo pessoal/investimento) e por empresa pagadora (SPM/FD), e para dividir uma transação (tipicamente fatura de cartão) em múltiplas alocações. Ao fim, o card "Via FD" / "Pessoal Hugo" / "Investimento Hugo" do `/dashboard/saidas` sai de R$ 0 e passa a refletir realidade.

**Architecture:**
- Backend: schema `OrcamentoLinhaPatch` ganha `bolso` + `empresa_pagadora_id`; 3 endpoints novos para `transacao_linha`.
- Frontend: 2 selects reutilizáveis + modal de edição de linha ampliado + página de split de transação.
- Dashboard: `/saidas` e KPIs passam a somar por bolso real (query ajustada no backend).

**Tech Stack:** Python FastAPI + Supabase httpx (backend), Next.js 16 / React 19 / Tailwind 4 (frontend). Schema Pydantic já tem `BolsoTipo` enum (criado no Plano 01 em `backend/api/schemas/bolso.py`).

**Spec:** `docs/superpowers/specs/2026-04-22-dashboard-e-bolsos-design.md`
**Planos anteriores:** Plano 01 (schema + fixes) + Plano 02 (home refinada) — ambos completos e em produção.

---

## File Structure

Arquivos criados:

```
backend/api/routers/
  transacao_linha.py                          — 3 endpoints: GET/POST/DELETE /transacoes/{id}/split + padrão por titular

backend/tests/
  test_transacao_linha.py                     — cobertura dos 3 endpoints + invariante soma

frontend/components/ui/
  bolso-select.tsx                            — select de BolsoTipo (4 opções + labels humanos)
  empresa-pagadora-select.tsx                 — select de empresa do grupo (SPM/FD/nenhuma)

frontend/components/orcamento/
  linha-editor-modal.tsx                      — modal de edição de orcamento_linha (atualiza existente ou cria novo)

frontend/components/transacoes/
  split-editor.tsx                            — form de split de transação (array editável de linhas)

frontend/app/(authed)/transacoes/
  [id]/split/
    page.tsx                                  — página de split por transação_bancaria
```

Arquivos modificados:

```
backend/api/schemas/orcamento.py              — OrcamentoLinhaOut + OrcamentoLinhaPatch ganham bolso + empresa_pagadora_id
backend/api/schemas/transacao_linha.py        — NOVO: schemas do split (TransacaoLinhaCreate, TransacaoLinhaOut, SplitRequest)
backend/api/main.py                           — registra router transacao_linha
backend/api/routers/dashboard.py              — filtra por bolso quando competência tem linhas classificadas
backend/api/routers/dashboard_evolucao.py     — não muda
frontend/types/v2.ts                          — TransacaoLinha, SplitRequest, OrcamentoLinha.bolso, empresa_pagadora_id
frontend/lib/api/transacoes.ts                — NOVO ou estende: fetchSplit, saveSplit, deleteSplit
frontend/lib/api/orcamento.ts                 — patchLinha já existe; ajustar tipo
frontend/app/(authed)/orcamento/page.tsx      — lista passa a mostrar badge [FD] + coluna Bolso; ao clicar, abre linha-editor-modal
frontend/app/(authed)/dashboard/saidas/page.tsx — passa a consumir valores reais por bolso (em vez do stub de R$ 0)
```

---

## Task 1: Backend — schemas ampliados + 3 endpoints de split

**Files:** ver File Structure acima.

- [ ] **Step 1: Estender `backend/api/schemas/orcamento.py`**

Adicionar imports e campos. Em `OrcamentoLinhaOut` e `OrcamentoLinhaPatch`, incluir:

```python
from backend.api.schemas.bolso import BolsoTipo
from uuid import UUID
from typing import Optional

# dentro da classe OrcamentoLinhaOut:
    bolso: BolsoTipo = BolsoTipo.SPM_OPERACIONAL
    empresa_pagadora_id: Optional[UUID] = None

# dentro da classe OrcamentoLinhaPatch:
    bolso: Optional[BolsoTipo] = None
    empresa_pagadora_id: Optional[UUID] = None  # enviar null explícito pra limpar
```

O `PATCH /orcamentos/linhas/{linha_id}` já faz `payload.model_dump(exclude_unset=True)` — os dois novos campos passam automaticamente se enviados.

- [ ] **Step 2: Criar `backend/api/schemas/transacao_linha.py`**

```python
"""Schemas Pydantic para split de transação (Track B Fase D)."""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from backend.api.schemas.bolso import BolsoTipo


class TransacaoLinhaCreate(BaseModel):
    valor: float = Field(..., description="Valor da linha. Sinal segue o da transação pai.")
    bolso: BolsoTipo
    orcamento_linha_id: Optional[UUID] = None
    empresa_pagadora_id: Optional[UUID] = None
    descricao: Optional[str] = None


class TransacaoLinhaOut(TransacaoLinhaCreate):
    id: UUID
    transacao_bancaria_id: UUID
    criado_em: str
    criado_por: Optional[UUID] = None


class SplitRequest(BaseModel):
    linhas: List[TransacaoLinhaCreate]


class SplitResponse(BaseModel):
    transacao_bancaria_id: UUID
    valor_transacao: float
    valor_soma_linhas: float
    linhas: List[TransacaoLinhaOut]
```

- [ ] **Step 3: Criar `backend/api/routers/transacao_linha.py`**

```python
"""Router /transacoes/{id}/split — split de uma transação em N alocações.

Invariante: sum(linhas.valor) = transacao_bancaria.valor (±0.01).
Validado no POST. Linhas anteriores são deletadas atomicamente antes do INSERT.
"""
from decimal import Decimal
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.transacao_linha import (
    SplitRequest,
    SplitResponse,
    TransacaoLinhaOut,
)


router = APIRouter(tags=["transacao_linha"])

TOLERANCIA = Decimal("0.01")


@router.get("/transacoes/{tx_id}/split", response_model=SplitResponse)
def get_split(tx_id: UUID, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    tx = client.table("transacao_bancaria").select("id,valor").eq("id", str(tx_id)).limit(1).execute().data
    if not tx:
        raise HTTPException(404, detail={"error": "Transação não encontrada"})
    linhas = (
        client.table("transacao_linha")
        .select("*")
        .eq("transacao_bancaria_id", str(tx_id))
        .order("criado_em")
        .execute()
        .data
        or []
    )
    soma = sum(float(l["valor"]) for l in linhas)
    return SplitResponse(
        transacao_bancaria_id=tx_id,
        valor_transacao=float(tx[0]["valor"]),
        valor_soma_linhas=round(soma, 2),
        linhas=[TransacaoLinhaOut(**l) for l in linhas],
    )


@router.post("/transacoes/{tx_id}/split", response_model=SplitResponse, status_code=status.HTTP_200_OK)
def save_split(tx_id: UUID, payload: SplitRequest, current=Depends(get_current_user)):
    """Substitui todo o split da transação. Linhas existentes são deletadas."""
    if not payload.linhas:
        raise HTTPException(400, detail={"error": "Pelo menos uma linha é obrigatória"})

    client = get_supabase_authed(current["jwt"])
    tx = client.table("transacao_bancaria").select("id,valor").eq("id", str(tx_id)).limit(1).execute().data
    if not tx:
        raise HTTPException(404, detail={"error": "Transação não encontrada"})
    valor_tx = Decimal(str(tx[0]["valor"]))
    soma = sum(Decimal(str(l.valor)) for l in payload.linhas)
    if abs(soma - valor_tx) > TOLERANCIA:
        raise HTTPException(
            400,
            detail={
                "error": "Soma das linhas diverge do valor da transação",
                "valor_transacao": float(valor_tx),
                "valor_soma_linhas": float(soma),
            },
        )

    # Atomicidade best-effort: delete + insert sequencial.
    client.table("transacao_linha").delete().eq("transacao_bancaria_id", str(tx_id)).execute()
    rows = [
        {
            "transacao_bancaria_id": str(tx_id),
            "valor": float(l.valor),
            "bolso": l.bolso.value,
            "orcamento_linha_id": str(l.orcamento_linha_id) if l.orcamento_linha_id else None,
            "empresa_pagadora_id": str(l.empresa_pagadora_id) if l.empresa_pagadora_id else None,
            "descricao": l.descricao,
            "criado_por": current.get("id"),
        }
        for l in payload.linhas
    ]
    inserted = client.table("transacao_linha").insert(rows).execute().data or []
    return SplitResponse(
        transacao_bancaria_id=tx_id,
        valor_transacao=float(valor_tx),
        valor_soma_linhas=float(soma),
        linhas=[TransacaoLinhaOut(**l) for l in inserted],
    )


@router.delete("/transacoes/{tx_id}/split", status_code=status.HTTP_204_NO_CONTENT)
def delete_split(tx_id: UUID, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    client.table("transacao_linha").delete().eq("transacao_bancaria_id", str(tx_id)).execute()
    return None


@router.get("/transacoes/{tx_id}/split/sugerir", response_model=SplitResponse)
def sugerir_split_do_ultimo(tx_id: UUID, current=Depends(get_current_user)):
    """Busca o último split feito para uma transação do mesmo titular_pix.

    Se existir, retorna as proporções adaptadas ao valor da transação atual.
    Útil para fatura de cartão recorrente do mesmo titular.
    """
    client = get_supabase_authed(current["jwt"])
    tx = (
        client.table("transacao_bancaria")
        .select("id,valor,titular_pix")
        .eq("id", str(tx_id))
        .limit(1)
        .execute()
        .data
    )
    if not tx:
        raise HTTPException(404, detail={"error": "Transação não encontrada"})
    titular = (tx[0].get("titular_pix") or "").strip().upper()
    if not titular:
        return SplitResponse(
            transacao_bancaria_id=tx_id,
            valor_transacao=float(tx[0]["valor"]),
            valor_soma_linhas=0.0,
            linhas=[],
        )

    # Busca transações anteriores do mesmo titular com split
    anteriores = (
        client.table("transacao_bancaria")
        .select("id,valor,data_extrato")
        .ilike("titular_pix", titular)
        .neq("id", str(tx_id))
        .order("data_extrato", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )
    for ant in anteriores:
        linhas = (
            client.table("transacao_linha")
            .select("*")
            .eq("transacao_bancaria_id", ant["id"])
            .execute()
            .data
            or []
        )
        if linhas:
            valor_atual = Decimal(str(tx[0]["valor"]))
            valor_ant = Decimal(str(ant["valor"]))
            if valor_ant == 0:
                continue
            ratio = valor_atual / valor_ant
            proporcionais = []
            for l in linhas:
                proporcionais.append({
                    **l,
                    "id": str(l["id"]),
                    "transacao_bancaria_id": str(tx_id),
                    "valor": float(round(Decimal(str(l["valor"])) * ratio, 2)),
                })
            return SplitResponse(
                transacao_bancaria_id=tx_id,
                valor_transacao=float(valor_atual),
                valor_soma_linhas=sum(p["valor"] for p in proporcionais),
                linhas=[TransacaoLinhaOut(**p) for p in proporcionais],
            )
    # nenhum split anterior encontrado
    return SplitResponse(
        transacao_bancaria_id=tx_id,
        valor_transacao=float(tx[0]["valor"]),
        valor_soma_linhas=0.0,
        linhas=[],
    )
```

- [ ] **Step 4: Registrar router em `backend/api/main.py`**

```python
from backend.api.routers import (
    ...,
    transacao_linha,
)
...
app.include_router(transacao_linha.router)
```

- [ ] **Step 5: Criar `backend/tests/test_transacao_linha.py`** cobrindo:
  - `test_get_split_vazio_retorna_valor_transacao` — transação sem split, retorna soma=0
  - `test_post_split_valida_soma_igual_valor` — soma divergente retorna 400
  - `test_post_split_substitui_anterior` — chama 2x, só as linhas do segundo ficam
  - `test_post_split_soma_bate` — 2 linhas R$50 cada pra transação R$100 → 200 OK
  - `test_delete_split_remove_linhas`
  - `test_sugerir_usa_proporcao_do_mes_anterior`

- [ ] **Step 6: Rodar suite**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro-trackb && .venv/bin/python -m pytest backend/tests/ --tb=line
```

Expected: passing + 6 novos tests.

- [ ] **Step 7: Aplicar migrations via MCP** — NÃO é necessário, já estão em produção desde Plano 01.

- [ ] **Step 8: Commit**

```bash
git add backend/api/schemas/orcamento.py backend/api/schemas/transacao_linha.py backend/api/routers/transacao_linha.py backend/api/main.py backend/tests/test_transacao_linha.py
git commit -m "feat(track-b): endpoints de split de transação + schema orcamento_linha ganha bolso/empresa_pagadora"
```

---

## Task 2: Frontend — selects de Bolso e Empresa Pagadora

**Files:**
- Create: `frontend/components/ui/bolso-select.tsx`, `empresa-pagadora-select.tsx`
- Modify: `frontend/types/v2.ts`

- [ ] **Step 1: Atualizar types** em `frontend/types/v2.ts` — adicionar ao final:

```typescript
export type BolsoTipo = "SPM_OPERACIONAL" | "FD_VIA_SPM" | "HUGO_PESSOAL" | "INVESTIMENTO_HUGO"

export const BOLSO_LABELS: Record<BolsoTipo, string> = {
  SPM_OPERACIONAL: "SPM operacional",
  FD_VIA_SPM: "Via FD",
  HUGO_PESSOAL: "Pessoal Hugo",
  INVESTIMENTO_HUGO: "Investimento Hugo",
}

export interface EmpresaGrupo {
  id: string
  codigo: string
  razao_social: string
  papel: "PRINCIPAL" | "INTRAGRUPO"
}

export interface TransacaoLinha {
  id: string
  transacao_bancaria_id: string
  valor: number
  bolso: BolsoTipo
  orcamento_linha_id: string | null
  empresa_pagadora_id: string | null
  descricao: string | null
  criado_em: string
}

export interface SplitRequest {
  linhas: Array<{
    valor: number
    bolso: BolsoTipo
    orcamento_linha_id?: string | null
    empresa_pagadora_id?: string | null
    descricao?: string | null
  }>
}

export interface SplitResponse {
  transacao_bancaria_id: string
  valor_transacao: number
  valor_soma_linhas: number
  linhas: TransacaoLinha[]
}
```

Também ampliar `OrcamentoLinhaOut` existente se já estiver tipada com os campos antigos: adicionar `bolso: BolsoTipo` e `empresa_pagadora_id: string | null`.

- [ ] **Step 2: Criar `frontend/components/ui/bolso-select.tsx`**

```typescript
"use client"

import type { BolsoTipo } from "@/types/v2"
import { BOLSO_LABELS } from "@/types/v2"

interface Props {
  value: BolsoTipo
  onChange: (v: BolsoTipo) => void
  disabled?: boolean
}

export function BolsoSelect({ value, onChange, disabled }: Props) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as BolsoTipo)}
      disabled={disabled}
      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white"
    >
      {(Object.keys(BOLSO_LABELS) as BolsoTipo[]).map((b) => (
        <option key={b} value={b}>
          {BOLSO_LABELS[b]}
        </option>
      ))}
    </select>
  )
}
```

- [ ] **Step 3: Criar `frontend/components/ui/empresa-pagadora-select.tsx`**

```typescript
"use client"

import { useEffect, useState } from "react"
import { apiClient } from "@/lib/api"
import type { EmpresaGrupo } from "@/types/v2"

interface Props {
  value: string | null
  onChange: (id: string | null) => void
  disabled?: boolean
}

export function EmpresaPagadoraSelect({ value, onChange, disabled }: Props) {
  const [empresas, setEmpresas] = useState<EmpresaGrupo[]>([])
  useEffect(() => {
    apiClient.get<EmpresaGrupo[]>("/empresas").then((r) => setEmpresas(r.data)).catch(() => setEmpresas([]))
  }, [])
  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      disabled={disabled}
      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white"
    >
      <option value="">Nenhuma (pago direto pela SPM)</option>
      {empresas.map((e) => (
        <option key={e.id} value={e.id}>
          {e.codigo} — {e.razao_social}
        </option>
      ))}
    </select>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/types/v2.ts frontend/components/ui/bolso-select.tsx frontend/components/ui/empresa-pagadora-select.tsx
git commit -m "feat(track-b): selects Bolso e Empresa Pagadora reutilizáveis"
```

---

## Task 3: Modal de edição de linha do orçamento com bolso + empresa pagadora

**Files:**
- Create: `frontend/components/orcamento/linha-editor-modal.tsx`
- Modify: `frontend/app/(authed)/orcamento/page.tsx` (abre modal ao clicar em linha, mostra coluna Bolso e badge [FD])
- Modify: `frontend/lib/api/orcamento.ts` (se função patch ainda não existe)

- [ ] **Step 1: Criar modal** com formulário:
  - Campos readonly: titular_razao_social, categoria
  - Campos editáveis: valor_previsto, data_previsao, bolso (BolsoSelect), empresa_pagadora_id (EmpresaPagadoraSelect)
  - Botões: Cancelar · Salvar
  - Ao salvar, chama `PATCH /orcamentos/linhas/{linha_id}` com body parcial

- [ ] **Step 2: Ajustar lista do orçamento** (`orcamento/page.tsx`):
  - Linha ganha badge `[FD]` pequeno à direita do titular quando `empresa_pagadora_id` existir
  - Coluna "Bolso" entre "Categoria" e "Valor previsto", mostrando `BOLSO_LABELS[linha.bolso]` com cor (SPM operacional = cinza, FD = amarelo, Pessoal = vermelho, Investimento = roxo)
  - Ao clicar em linha, abre o modal de edição

- [ ] **Step 3: Smoke manual** — editar uma linha existente, salvar, recarregar, conferir que bolso e badge persistiram

- [ ] **Step 4: Commit**

```bash
git add frontend/components/orcamento/linha-editor-modal.tsx "frontend/app/(authed)/orcamento/page.tsx" frontend/lib/api/orcamento.ts
git commit -m "feat(track-b): orçamento edita bolso + empresa pagadora com badge [FD] na lista"
```

---

## Task 4: Tela de split de transação

**Files:**
- Create: `frontend/components/transacoes/split-editor.tsx`
- Create: `frontend/app/(authed)/transacoes/[id]/split/page.tsx`
- Create: `frontend/lib/api/transacoes.ts` (se ainda não existe)

- [ ] **Step 1: `frontend/lib/api/transacoes.ts`**

```typescript
import { apiClient } from "@/lib/api"
import type { SplitResponse, SplitRequest } from "@/types/v2"

export const fetchSplit = (id: string) =>
  apiClient.get<SplitResponse>(`/transacoes/${id}/split`).then(r => r.data)

export const fetchSplitSugerido = (id: string) =>
  apiClient.get<SplitResponse>(`/transacoes/${id}/split/sugerir`).then(r => r.data)

export const saveSplit = (id: string, body: SplitRequest) =>
  apiClient.post<SplitResponse>(`/transacoes/${id}/split`, body).then(r => r.data)

export const deleteSplit = (id: string) =>
  apiClient.delete(`/transacoes/${id}/split`)
```

- [ ] **Step 2: `split-editor.tsx`** — componente controlado:
  - Props: `{ transacao: { id, valor, titular_pix, descricao, data_extrato }, inicial: TransacaoLinha[] }`
  - Estado: lista editável de linhas `{ valor, bolso, descricao }`
  - Linha default quando vazio: `[{ valor: props.transacao.valor, bolso: "SPM_OPERACIONAL" }]`
  - Botões de atalho no topo:
    - "50/50 SPM/Hugo pessoal" → 2 linhas metade cada
    - "Copiar divisão do mês anterior" → chama `fetchSplitSugerido(id)` e substitui as linhas
  - Linha editável:
    - Input numérico de valor (R$)
    - BolsoSelect
    - Input texto de descrição (opcional)
    - Botão lixeira remove a linha
  - Botão "+ Adicionar linha" abaixo
  - Resumo no rodapé:
    - Valor da transação (R$ X)
    - Soma das linhas (R$ Y)
    - Diferença (R$ Z) em verde se = 0, vermelho caso contrário
  - Botão Salvar desabilitado se diferença > 0.01
  - Botão Cancelar volta pra onde veio (history.back)

- [ ] **Step 3: `page.tsx`** da rota `/transacoes/[id]/split`:
  - Busca `transacao_bancaria` por id (usa endpoint existente ou cria `GET /transacoes/{id}` se necessário — checar no backend)
  - Busca split atual via `fetchSplit`
  - Se split atual vazio, pode buscar sugestão (`fetchSplitSugerido`) e pré-preencher
  - Renderiza `<SplitEditor ...>` com os dados

- [ ] **Step 4: Adicionar link "Dividir" na tela de conciliação** existente (ou onde a transação é visualizada). Não precisa refatorar conciliação inteira — só adicionar um link discreto.

- [ ] **Step 5: Smoke manual** — abrir split de uma transação (qualquer uma), dividir em 2 linhas SPM/pessoal, salvar, recarregar, confirmar que as linhas estão lá.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/transacoes/ "frontend/app/(authed)/transacoes/" frontend/lib/api/transacoes.ts
git commit -m "feat(track-b): split de transação com atalho 50/50 e copiar mês anterior"
```

---

## Task 5: Dashboard /saidas consome valores reais por bolso

**Files:**
- Modify: `backend/api/routers/dashboard.py` (ou criar helper)
- Modify: `frontend/app/(authed)/dashboard/saidas/page.tsx`

Quando houver linhas de orçamento classificadas por bolso e linhas de split de transação, os totais dos 4 cards em `/dashboard/saidas` passam a ter valor real.

- [ ] **Step 1: Backend — endpoint `GET /dashboard/saidas-por-bolso?competencia=YYYY-MM`**

Agrega:
- Transações diretas: para cada `transacao_bancaria` tipo=DEBITO no período, se ela tiver `transacao_linha` filhas, soma por bolso; senão, considera tudo `SPM_OPERACIONAL` (fallback).
- Retorna: `{ spm_operacional: float, fd_via_spm: float, hugo_pessoal: float, investimento_hugo: float, total: float }`

- [ ] **Step 2: Frontend** — `/dashboard/saidas/page.tsx` passa a buscar esse endpoint em vez de assumir 100% SPM. Cada `<BolsoCard>` recebe valor real + calcula % sobre o total.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(track-b): /dashboard/saidas usa totais reais por bolso"
```

---

## Task 6: Deploy + smoke

- [ ] **Step 1: Rodar suite completa**

```bash
.venv/bin/python -m pytest backend/tests/ --tb=line
```

- [ ] **Step 2: Build frontend**

```bash
cd frontend && ./node_modules/.bin/next build
```

- [ ] **Step 3: Merge para main**

```bash
git checkout main && git merge feature/track-b-dashboard-bolsos --no-ff -m "Merge Plano 03: UI bolsos + split de transação" && git push
```

- [ ] **Step 4: Sync temp-d**

```bash
rsync -a --delete --exclude='.git' --exclude='node_modules' --exclude='.venv' --exclude='.next' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.superpowers' /Users/dr.damasceno/spm-sistemafinanceiro/ /tmp/spm-deploy-temp-d/
cd /tmp/spm-deploy-temp-d && git add -A && git commit -m "sync: Plano 03 UI bolsos + split" && git push
```

- [ ] **Step 5: Smoke manual pelo Hugo**
  - Editar uma linha de orçamento com bolso=FD_VIA_SPM → badge aparece, `/dashboard/saidas` mostra valor no card Via FD
  - Dividir uma transação em 2 linhas (SPM/pessoal) → `/dashboard/saidas` reflete
  - 5 stubs continuam OK

---

## Self-review

### Cobertura do spec §3 (modelo) e §6 (UI)

- ✅ Spec §3.1 coluna `orcamento_linha.bolso` e `empresa_pagadora_id` (Task 1 Step 1)
- ✅ Spec §3.1 tabela `transacao_linha` (já migrada no Plano 01; endpoints no Task 1 Step 3)
- ✅ Spec §6.3 UI de bolso em orçamento (Task 3)
- ✅ Spec §6.4 split de transação com atalhos + memorização (Task 4)
- ✅ `/dashboard/saidas` reflete valores reais por bolso (Task 5)

### Fora deste plano (fica para Plano 04)

- Conciliação em lote PIX→FD com flag retrocompat
- Filtro de prestadores com `pj_empregadora_id` do pool individual
- Regra FIFO por competência para consumir linhas FD

### Riscos

| Risco | Mitigação |
|---|---|
| Split manual tem curva de aprendizado | Atalhos 50/50 + copiar mês anterior; texto explicativo na tela |
| Soma das linhas ≠ valor da tx → split inválido | Validação client-side + 400 do backend |
| Delete+insert em `transacao_linha` não é atômico (supabase-py sem transação) | Aceitável no MVP; cada POST substitui totalmente o split anterior, então estado intermediário só aparece durante operação de ~ms |
| Hugo classifica 1 linha por semana e os cards de bolso ficam sempre zerados | Aceito — é a realidade do MVP; performance real vem após uso |
