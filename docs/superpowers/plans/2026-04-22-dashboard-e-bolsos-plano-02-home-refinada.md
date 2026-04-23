# Track B — Plano 02: Home refinada (Fase C)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganizar a home do Dashboard em 3 zonas cognitivas (agora / mês / tendência), adicionar cards novos (Evolução do Caixa + sparkline, Receita Financeira, Compromissos, Recebíveis) e rodapé com 4 gráficos de tendência 6m. Remover da home os 2 gráficos atuais (Donut "Saídas por natureza" + Barras "Previsto × Realizado") — eles migram para subpágina `/dashboard/saidas`.

**Architecture:** Backend ganha 5 endpoints novos. Frontend ganha componente `<Sparkline />` genérico + 4 cards novos + 4 gráficos SVG puros (sem lib externa). Home é refatorada no arquivo `page.tsx`. Subpágina `/dashboard/saidas` é criada como stub que mostra os 4 bolsos (drill-down completo fica para Plano 03).

**Tech Stack:** Next.js 16.2, React 19, Tailwind 4, FastAPI, Supabase. SVG inline para todos os gráficos (sem dep nova — recharts/d3 evitados).

**Spec:** `docs/superpowers/specs/2026-04-22-dashboard-e-bolsos-design.md`
**Plano 01 (pré-requisito):** `2026-04-22-dashboard-e-bolsos-plano-01-schema-e-fixes.md` — COMPLETADO

---

## File Structure

Arquivos criados:

```
backend/api/schemas/
  dashboard_v2.py                                 — schemas dos 5 endpoints novos

backend/api/routers/
  dashboard_evolucao.py                           — GET /dashboard/evolucao-caixa
  dashboard_compromissos_recebiveis.py            — GET /dashboard/compromissos, /recebiveis
  dashboard_receita_financeira.py                 — GET /dashboard/receita-financeira
  dashboard_historico.py                          — GET /dashboard/historico

backend/tests/
  test_dashboard_evolucao.py
  test_dashboard_compromissos.py
  test_dashboard_recebiveis.py
  test_dashboard_receita_financeira.py
  test_dashboard_historico.py

frontend/components/ui/
  sparkline.tsx                                   — genérico reutilizável

frontend/components/dashboard/
  evolucao-caixa-card.tsx
  receita-financeira-card.tsx
  compromissos-card.tsx
  recebiveis-card.tsx

frontend/components/dashboard/tendencia/
  index.tsx                                       — wrapper com 4 gráficos
  crescimento-caixa.tsx
  faturamento.tsx
  despesas-por-tipo.tsx                           — com tooltip hover
  posicao-em-aberto.tsx                           — com 3 números-chave

frontend/app/(authed)/dashboard/saidas/
  page.tsx                                        — stub com 4 bolsos
```

Arquivos modificados:

```
backend/api/main.py                               — registra 4 routers novos
frontend/types/v2.ts                              — types dos novos endpoints
frontend/lib/api/dashboard.ts                     — 5 funções de fetch novas
frontend/app/(authed)/page.tsx                    — home refatorada
```

Arquivos MOVIDOS para subpágina (removidos da home, usados em `/saidas`):
```
frontend/components/dashboard/donut-naturezas.tsx     — sem mudança, só deixa de ser usado na home
frontend/components/dashboard/barras-pxr.tsx          — idem
```

---

## Task 1: Backend — endpoints novos + schemas + TS types

**Files:**
- Create: `backend/api/schemas/dashboard_v2.py`, 4 routers novos, 5 test files
- Modify: `backend/api/main.py`, `frontend/types/v2.ts`, `frontend/lib/api/dashboard.ts`

### Schemas (dashboard_v2.py)

```python
"""Schemas dos endpoints v2 do Dashboard (Track B)."""
from typing import List, Optional
from pydantic import BaseModel


class EvolucaoCaixaResponse(BaseModel):
    abertura_data: str      # "2026-04-01"
    abertura_valor: float
    hoje_data: str          # "2026-04-22"
    hoje_valor: float
    variacao_valor: float
    variacao_pct: float
    sparkline: List[float]  # valores diários consolidados para o mês


class CompromissoItem(BaseModel):
    fonte: str              # "PP" ou "FATURA"
    descricao: str
    valor: float
    vencimento: Optional[str]


class CompromissosResponse(BaseModel):
    total: float
    por_fonte: dict         # {"PP": 1_000_000, "FATURAS": 147_000}
    itens: List[CompromissoItem]


class RecebivelItem(BaseModel):
    contratante: str
    valor: float
    dias_atraso: int
    faixa_aging: str        # "0-30", "30-60", "60-90", "90+"


class RecebiveisResponse(BaseModel):
    total: float
    por_aging: dict         # {"0-30": ..., "30-60": ...}
    itens: List[RecebivelItem]


class ReceitaFinanceiraResponse(BaseModel):
    rendimento_mes: float
    acumulado_ano: float
    rentabilidade_pct: float
    cdi_mes_pct: float
    percent_cdi: float


class MesHistorico(BaseModel):
    competencia: str        # "2026-04"
    liquidez: float
    faturamento: float
    despesa_fixa: float
    despesa_variavel: float
    tributo: float
    compromissos_abertos: float
    recebiveis_atraso: float


class HistoricoResponse(BaseModel):
    meses: List[MesHistorico]
```

### Endpoints (implementação de referência — um exemplo por endpoint)

**dashboard_evolucao.py** — `/dashboard/evolucao-caixa?competencia=YYYY-MM`:
- Lê `saldo_caixa_diario` da competência pra pegar abertura (dia 1) e hoje
- Calcula variação = hoje - abertura
- Sparkline = lista dos `liquidez_total` de cada dia da competência até hoje
- Se `saldo_caixa_diario` vazio (Plano 05 ainda não implementou worker), retorna fallback usando `get_liquidez_total` atual + placeholders

**dashboard_compromissos_recebiveis.py** — dois endpoints:
- `/dashboard/compromissos`: soma de `registro_pp WHERE status_saldo='ELEGIVEL'` (agrupado por empresa), menos `transacao_bancaria` já conciliadas; + linhas de orçamento com `data_previsao <= today+30d` sem conciliação
- `/dashboard/recebiveis`: linhas de orçamento com sinal de entrada e `data_previsao < today` sem conciliação, agrupadas por contratante, com faixas de aging (0-30d, 30-60d, 60-90d, 90d+)

**dashboard_receita_financeira.py** — `/dashboard/receita-financeira?competencia=YYYY-MM`:
- Rendimento mês = soma de `transacao_bancaria WHERE natureza='RECEITA_FINANCEIRA'` + `aplicacao_financeira.rendimento_ultima_atualizacao` (se fonte=MANUAL)
- Acumulado ano = mesma lógica ampliada
- Rentabilidade % = rendimento_mes / saldo_medio_mes
- CDI mês = constante de config (Cadastros futuro) ou hardcode 0,83% por enquanto
- % CDI = rentabilidade / cdi_mes

**dashboard_historico.py** — `/dashboard/historico?meses=6`:
- Para cada competência dos últimos N meses, agrega liquidez (ultimo saldo_caixa_diario do mês), faturamento (créditos), despesas por tipo (DESPESA_FIXA / VARIAVEL / TRIBUTO), compromissos em aberto e recebíveis atrasados
- Retorna lista ordenada por competência

**Passos bite-sized (agrupados por endpoint):**

- [ ] **Step 1: Criar `backend/api/schemas/dashboard_v2.py`** com todos os schemas acima

- [ ] **Step 2: Criar 4 routers** em `backend/api/routers/dashboard_*.py`, cada um com seu endpoint

- [ ] **Step 3: Registrar routers em `backend/api/main.py`**

```python
from backend.api.routers import (
    dashboard_evolucao,
    dashboard_compromissos_recebiveis,
    dashboard_receita_financeira,
    dashboard_historico,
)

app.include_router(dashboard_evolucao.router)
app.include_router(dashboard_compromissos_recebiveis.router)
app.include_router(dashboard_receita_financeira.router)
app.include_router(dashboard_historico.router)
```

- [ ] **Step 4: Criar 5 test files** — testes unitários usando MagicMock (sem live Supabase)

- [ ] **Step 5: Rodar suite completa**

```bash
.venv/bin/python -m pytest backend/tests/ -v --tb=short
```

Expected: passing + 5 novos tests.

- [ ] **Step 6: Atualizar `frontend/types/v2.ts`** com os novos response types (cópia fiel dos Pydantic)

- [ ] **Step 7: Adicionar 5 fetch functions em `frontend/lib/api/dashboard.ts`**

```typescript
export async function fetchEvolucaoCaixa(competencia: string): Promise<EvolucaoCaixaResponse> { ... }
export async function fetchCompromissos(): Promise<CompromissosResponse> { ... }
export async function fetchRecebiveis(): Promise<RecebiveisResponse> { ... }
export async function fetchReceitaFinanceira(competencia: string): Promise<ReceitaFinanceiraResponse> { ... }
export async function fetchHistorico(meses: number = 6): Promise<HistoricoResponse> { ... }
```

- [ ] **Step 8: Commit**

```bash
git add backend/api/schemas/dashboard_v2.py backend/api/routers/dashboard_*.py backend/api/main.py backend/tests/test_dashboard_*.py frontend/types/v2.ts frontend/lib/api/dashboard.ts
git commit -m "feat(track-b): 5 endpoints novos do dashboard — evolucao, compromissos, recebiveis, receita financeira, historico"
```

---

## Task 2: Componente Sparkline

**Files:**
- Create: `frontend/components/ui/sparkline.tsx`

- [ ] **Step 1: Criar componente SVG puro**

```typescript
interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  color?: string
  fillGradient?: boolean
}

export function Sparkline({
  data,
  width = 200,
  height = 50,
  color = "#1e40af",
  fillGradient = true,
}: SparklineProps) {
  if (data.length < 2) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  // Normaliza para coordenadas 0..100 no eixo X e padding vertical de 4px
  const stepX = 100 / (data.length - 1)
  const points = data.map((v, i) => ({
    x: i * stepX,
    y: height - 4 - ((v - min) / range) * (height - 8),
  }))

  const pathLine = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x * width / 100},${p.y}`).join(" ")
  const pathArea = `${pathLine} L${width},${height} L0,${height} Z`
  const last = points[points.length - 1]
  const gradId = `spark-${Math.random().toString(36).slice(2, 9)}`

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height }} preserveAspectRatio="none">
      {fillGradient && (
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.25} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
      )}
      {fillGradient && <path d={pathArea} fill={`url(#${gradId})`} />}
      <path d={pathLine} fill="none" stroke={color} strokeWidth={2} />
      <circle cx={last.x * width / 100} cy={last.y} r={3} fill={color} />
    </svg>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/ui/sparkline.tsx
git commit -m "feat(track-b): componente Sparkline genérico SVG puro"
```

---

## Task 3: Cards novos (Evolução, Receita Financeira, Compromissos, Recebíveis)

**Files:**
- Create: `frontend/components/dashboard/evolucao-caixa-card.tsx`
- Create: `frontend/components/dashboard/receita-financeira-card.tsx`
- Create: `frontend/components/dashboard/compromissos-card.tsx`
- Create: `frontend/components/dashboard/recebiveis-card.tsx`

Cada card é componente `"use client"` que recebe props já tipadas (do Task 1).

### EvolucaoCaixaCard

```typescript
import type { EvolucaoCaixaResponse } from "@/types/v2"
import { formatBRL } from "@/lib/format"
import { Sparkline } from "@/components/ui/sparkline"

interface Props { data: EvolucaoCaixaResponse }

export function EvolucaoCaixaCard({ data }: Props) {
  const positive = data.variacao_valor >= 0
  return (
    <a href="/dashboard/saldo-diario"
       className="block p-5 bg-white border-2 border-blue-700 rounded-lg hover:shadow">
      <div className="flex justify-between items-baseline mb-3">
        <div className="text-xs font-bold text-blue-700 uppercase tracking-wide">
          Evolução do caixa
        </div>
        <div className="text-xs text-blue-700">Ver saldos diários →</div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_1fr_1.5fr] gap-4 items-center">
        <div>
          <div className="text-xs text-slate-500 uppercase">Abertura {fmtDate(data.abertura_data)}</div>
          <div className="text-lg font-bold tabular-nums">{formatBRL(data.abertura_valor)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 uppercase">Hoje {fmtDate(data.hoje_data)}</div>
          <div className="text-lg font-bold tabular-nums">{formatBRL(data.hoje_valor)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 uppercase">Variação</div>
          <div className={`text-lg font-bold tabular-nums ${positive ? "text-green-600" : "text-red-600"}`}>
            {positive ? "+" : ""}{formatBRL(data.variacao_valor)}
          </div>
          <div className={`text-xs ${positive ? "text-green-600" : "text-red-600"}`}>
            {positive ? "+" : ""}{data.variacao_pct.toFixed(2)}%
          </div>
        </div>
        <div className="hidden md:block">
          <Sparkline data={data.sparkline} />
        </div>
      </div>
    </a>
  )
}

function fmtDate(iso: string): string {
  const [, m, d] = iso.split("-")
  return `${d}/${m}`
}
```

### ReceitaFinanceiraCard

Card roxo com gradiente, 3 números: rendimento mês grande + acumulado ano + rentabilidade (com % CDI).

### CompromissosCard

Card laranja (amarelo-dourado), único número principal + linha secundária com breakdown (PP + Faturas).

### RecebiveisCard

Card vermelho, único número principal + contagem de contratantes em atraso.

- [ ] **Step 1-4:** criar os 4 componentes (um por step, um commit por task final)

- [ ] **Step 5: Commit consolidado**

```bash
git add frontend/components/dashboard/evolucao-caixa-card.tsx frontend/components/dashboard/receita-financeira-card.tsx frontend/components/dashboard/compromissos-card.tsx frontend/components/dashboard/recebiveis-card.tsx
git commit -m "feat(track-b): 4 cards novos da home — evolução, receita, compromissos, recebíveis"
```

---

## Task 4: 4 gráficos de tendência (rodapé)

**Files:** `frontend/components/dashboard/tendencia/{index,crescimento-caixa,faturamento,despesas-por-tipo,posicao-em-aberto}.tsx`

Cada gráfico é SVG puro. O wrapper `index.tsx` renderiza os 4 num grid 2×2 e busca `fetchHistorico(6)` uma vez.

- [ ] **Step 1: Criar `tendencia/crescimento-caixa.tsx`** — área com gradiente
- [ ] **Step 2: Criar `tendencia/faturamento.tsx`** — barras verticais
- [ ] **Step 3: Criar `tendencia/despesas-por-tipo.tsx`** — barras empilhadas (Fixa/Variável/Tributo) com tooltip no hover mostrando R$ e % de cada
- [ ] **Step 4: Criar `tendencia/posicao-em-aberto.tsx`** — linhas duplas (compromissos tracejado, recebíveis sólido) + 3 mini-cards acima (A receber / A pagar / Impacto)
- [ ] **Step 5: Criar `tendencia/index.tsx`** — wrapper com grid 2×2 e fetch

```typescript
"use client"
import { useEffect, useState } from "react"
import { fetchHistorico } from "@/lib/api/dashboard"
import type { HistoricoResponse } from "@/types/v2"
import { CrescimentoCaixa } from "./crescimento-caixa"
import { Faturamento } from "./faturamento"
import { DespesasPorTipo } from "./despesas-por-tipo"
import { PosicaoEmAberto } from "./posicao-em-aberto"

export function TendenciaGrid() {
  const [data, setData] = useState<HistoricoResponse | null>(null)
  useEffect(() => { fetchHistorico(6).then(setData).catch(console.error) }, [])
  if (!data) return <div className="text-slate-500">Carregando tendência…</div>
  return (
    <div className="bg-slate-50 rounded-lg p-4">
      <div className="text-xs font-bold text-slate-800 uppercase tracking-wide mb-3">
        Tendência · últimos {data.meses.length} meses
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <CrescimentoCaixa meses={data.meses} />
        <Faturamento meses={data.meses} />
        <DespesasPorTipo meses={data.meses} />
        <PosicaoEmAberto meses={data.meses} />
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/components/dashboard/tendencia/
git commit -m "feat(track-b): 4 gráficos de tendência 6m no rodapé da home"
```

---

## Task 5: Refatoração da home + subpágina /saidas stub

**Files:**
- Modify: `frontend/app/(authed)/page.tsx`
- Create: `frontend/app/(authed)/dashboard/saidas/page.tsx`

- [ ] **Step 1: Criar `frontend/app/(authed)/dashboard/saidas/page.tsx`** (stub que mostra os 4 bolsos como cards + usa DonutNaturezas e BarrasPxR herdados)

- [ ] **Step 2: Refatorar `frontend/app/(authed)/page.tsx`** — nova ordem:
  1. LiquidezBanner (mantém)
  2. ContasCorrentesSection + AplicacoesSection (mantém)
  3. **EvolucaoCaixaCard** (novo)
  4. "Pra onde foi o dinheiro" + KpisGrid — **"Saídas do mês" agora é link para `/dashboard/saidas`**
  5. Grid 2 cols: CompromissosCard + RecebiveisCard
  6. ReceitaFinanceiraCard
  7. TendenciaGrid (rodapé)
  8. AlertasList
- [ ] **Step 3: Remover** imports de `DonutNaturezas` e `BarrasPxR` da `page.tsx` (os arquivos continuam existindo para a subpágina)
- [ ] **Step 4: Smoke manual** — `npm run dev` + abrir localhost e verificar layout

- [ ] **Step 5: Commit**

```bash
git add frontend/app/
git commit -m "feat(track-b): refatora home — 6 blocos + rodapé de tendência, donut/barras → /saidas"
```

---

## Self-review

### Cobertura do spec §2 (layout home) e §5 (endpoints)

- ✅ Liquidez + Contas/Aplicações (permanece)
- ✅ Evolução do caixa + sparkline → Task 2 + 3
- ✅ Pra onde foi o dinheiro (KPIs — já feito no Plano 01)
- ✅ Compromissos em aberto → Task 1 + 3
- ✅ Recebíveis em atraso → Task 1 + 3
- ✅ Receita Financeira (card roxo) → Task 1 + 3
- ✅ 4 gráficos tendência 6m → Task 4
- ✅ Donut/Barras movidos para subpágina → Task 5
- ✅ Subpágina `/dashboard/saidas` (stub) → Task 5
- Subpáginas `/saldo-diario`, `/historico`, `/receita-financeira`, `/compromissos`, `/recebiveis` → **Plano 04 ou 05** (não neste plano). Links na home apontam para elas mas retornam 404 até então.

### Fora deste plano

- Worker `fn_recalcular_saldo_diario` — Plano 05. Sem ele, endpoint `/evolucao-caixa` usa fallback (liquidez_total hoje + sparkline vazio). Ainda funcional.
- Subpáginas completas de drill-down — Plano 04+
- Conciliação em lote PIX→FD — Plano 04
- UI de bolso em orcamento_linha — Plano 03

### Riscos

| Risco | Mitigação |
|---|---|
| `saldo_caixa_diario` vazio até Plano 05 → sparkline/evolução sem dados reais | Fallback no endpoint: retorna abertura=liquidez_atual, hoje=liquidez_atual, sparkline=[liquidez_atual] |
| Recebíveis requerem orçamento ter linhas de entrada (sinal +) — pode não ter no banco atual | Se query retorna vazio, card mostra "Sem recebíveis atrasados" (zero é informação válida) |
| Performance do histórico 6m (múltiplas agregações) | Query única por mês + cache client-side (useEffect roda uma vez) |
