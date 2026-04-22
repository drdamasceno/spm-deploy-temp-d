# SPM Sistema Financeiro v2 — Plano 3 (UI Next.js, M4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps usam checkbox (`- [ ]`).

**Goal:** Construir as 7 telas Next.js do sistema v2 sobre a base do Passo 5a (já tem login + auth por cookies + rodadas). Ao final da execução: localhost em `frontend/` com todas as rotas funcionando, integradas aos 8 routers do backend (Plano 2).

**Architecture:** Next.js 16 App Router + React 19 + Tailwind v4 + shadcn/ui + axios + cookies JWT. Filtros globais (empresa, competência) via React Context. Cada rota em seu próprio segmento. Tabelas no padrão `Data → Status` (regra da CI).

**Tech Stack:** Next.js 16 · React 19 · TypeScript · Tailwind v4 · shadcn/ui · lucide-react · axios · zod · react-hook-form · sonner (toast) · date-fns.

**Spec + Plano 2 como referência:**
- Telas: `docs/superpowers/specs/2026-04-20-sistema-financeiro-v2-design.md` (§6)
- Mockups: `.superpowers/brainstorm/3056-1776662200/content/` (conciliacao-v1, dashboard-contratos, orcamento-v2)
- Endpoints: Plano 2 (routers catalogos/orcamento/extratos/conciliacao/regra_classificacao/adiantamento/contratos_competencia/dashboard)

**Pré-requisitos (já entregue pelos Planos 1 e 2):**
- Backend rodando em `http://localhost:8000` (ou apontar via `NEXT_PUBLIC_API_BASE_URL`)
- 8 routers ativos, 70 testes passing
- `frontend/lib/api.ts` existente com padrão axios + cookies JWT
- `frontend/components/ui/` com shadcn já preparado

**Fora do escopo deste plano (vira Plano 4 ou próxima sessão):**
- Deploy Render/Vercel
- Dados reais em produção (M5 + M6 do spec)
- Responsivo mobile (desktop-first por decisão do spec)
- Testes e2e automatizados (Playwright) — smoke visual manual nesta fase

---

## File Structure

### Novos arquivos

```
frontend/
  app/
    (authed)/
      layout.tsx                          # Shell autenticado (topbar + nav + filtros globais)
      page.tsx                            # /  → Dashboard (home)
      conciliacao/page.tsx                # /conciliacao
      contratos/page.tsx                  # /contratos (lista)
      contratos/[id]/[competencia]/page.tsx  # /contratos/<id>/<YYYY-MM>
      orcamento/page.tsx                  # /orcamento
      adiantamentos/page.tsx              # /adiantamentos
      extratos/page.tsx                   # /extratos (upload + listagem)
      cadastros/page.tsx                  # /cadastros
  components/
    layout/topbar.tsx                     # Topbar com filtros globais + perfil
    layout/nav.tsx                        # Nav horizontal
    layout/filter-empresa.tsx             # Dropdown SPM/FD/TODAS
    layout/filter-competencia.tsx         # Dropdown mês
    dashboard/kpis-grid.tsx               # 4 cards KPI
    dashboard/donut-naturezas.tsx         # Donut chart (svg inline)
    dashboard/barras-pxr.tsx              # Previsto × Realizado
    dashboard/alertas-list.tsx            # Lista de alertas
    conciliacao/two-panel.tsx             # 2 colunas transações × orçamento
    conciliacao/row-transacao.tsx         # Linha de transação com badge de sugestão
    conciliacao/row-orcamento.tsx         # Linha de orçamento pendente
    contratos/contrato-card.tsx           # Card com DRE
    orcamento/tabs-secoes.tsx             # 6 abas por natureza
    orcamento/tabela-linhas.tsx           # Tabela editável das linhas
    orcamento/upload-xlsx-dialog.tsx      # Dialog de upload
    adiantamento/lista-tabela.tsx
    adiantamento/compensar-dialog.tsx
    extrato/upload-dialog.tsx             # Dialog que permite escolher tipo (Unicred PDF / Bradesco OFX)
    cadastros/tabs-entidades.tsx          # Tabs: projetos / categorias / contas / regras
    shared/status-badge.tsx               # Badge de status reutilizável (PAGO/PARC/PREV/VENC)
  lib/
    api/                                  # submodulos por recurso
      catalogos.ts
      orcamento.ts
      extratos.ts
      conciliacao.ts
      regra.ts
      adiantamento.ts
      contratos-competencia.ts
      dashboard.ts
    filters-context.tsx                   # React Context de filtros globais
  types/
    v2.ts                                 # Tipos dos 8 recursos v2 (EmpresaOut, OrcamentoOut, etc.)
```

### Arquivos modificados

```
frontend/
  middleware.ts                           # Muda redirect default: se autenticado e em /login → /  (era /rodadas)
  app/rodadas/page.tsx                    # Adicionar link para /adiantamentos + banner de adiantamentos abertos
```

### Responsabilidades

- `(authed)/layout.tsx`: shell único para todas as rotas autenticadas. Proteção via middleware já existente.
- `filters-context.tsx`: provê `empresa: 'SPM'|'FD'|'TODAS'` e `competencia: 'YYYY-MM'`. Persiste em localStorage.
- `lib/api/*.ts`: cada arquivo é um módulo fininho que encapsula fetches para um router. Todos usam o mesmo `axiosInstance` com credentials (`withCredentials: true` envia cookies).
- Componentes em `components/<tela>/`: lógica de apresentação. Nada de chamar API direto — sempre via `lib/api/`.

---

## M4-A — Fundação da app (2 tasks)

### Task 4.1: API client + types v2

**Files:**
- Create: `frontend/lib/api/catalogos.ts`, `orcamento.ts`, `extratos.ts`, `conciliacao.ts`, `regra.ts`, `adiantamento.ts`, `contratos-competencia.ts`, `dashboard.ts`
- Create: `frontend/types/v2.ts`
- Modify: `frontend/lib/api.ts` — exportar `apiClient` reutilizável

- [ ] **Step 1: Inspecionar `frontend/lib/api.ts` existente** e extrair a instância axios/fetch que já tem auth por cookie. Se já exportar um cliente reutilizável, ótimo. Se não, adicionar uma exportação `export const apiClient = ...` mantendo o que existe.

- [ ] **Step 2: Criar `frontend/types/v2.ts`** traduzindo os schemas Pydantic do Plano 2 para TypeScript:

```typescript
// frontend/types/v2.ts
export type EmpresaCodigo = "SPM" | "FD" | "TODAS";

export interface EmpresaOut {
  id: string;
  codigo: string;
  razao_social: string;
  cnpj: string | null;
  ativa: boolean;
}

export interface CategoriaOut {
  id: string;
  nome: string;
  descricao: string | null;
}

export interface ProjetoOut {
  id: string;
  codigo: string;
  descricao: string | null;
  empresa_id: string;
  ativo: boolean;
}

export type NaturezaOrcamento =
  | "DESPESA_FIXA"
  | "TRIBUTO"
  | "SALARIO_VARIAVEL"
  | "COMISSAO"
  | "VALOR_VARIAVEL"
  | "DESPESA_PROFISSIONAIS";

export interface OrcamentoOut {
  id: string;
  empresa_id: string;
  competencia: string;
  status: "RASCUNHO" | "VALIDADO" | "FECHADO";
  criado_em: string;
}

export interface OrcamentoLinhaOut {
  id: string;
  orcamento_id: string;
  natureza: NaturezaOrcamento;
  categoria_id: string | null;
  projeto_id: string | null;
  titular_cpf_cnpj: string | null;
  titular_razao_social: string;
  contrato_id: string | null;
  valor_previsto: number;
  data_previsao: string | null;
  observacao: string | null;
}

export interface ResultadoUploadOrcamento {
  orcamento_id: string;
  total_linhas_inseridas: number;
  linhas_por_secao: Record<NaturezaOrcamento, number>;
  linhas_descartadas: number;
  avisos: string[];
}

export interface UploadExtratoResponse {
  conta_id: string;
  origem_banco: "UNICRED" | "BRADESCO";
  total_transacoes_inseridas: number;
  periodo_inicio: string;
  periodo_fim: string;
  saldo_final: number;
}

export type OrigemSugestao = "REGRA" | "SIMILARIDADE" | "VALOR" | "MANUAL";

export interface SugestaoOut {
  transacao_id: string;
  orcamento_linha_id: string;
  confianca: number;
  origem: OrigemSugestao;
  valor_aplicado: number;
}

export interface ConciliacaoCreate {
  transacao_id: string;
  orcamento_linha_id: string;
  valor_aplicado: number;
  confianca: number | null;
  origem: OrigemSugestao;
}

export interface ConciliacaoOut extends ConciliacaoCreate {
  id: string;
  aprovada_em: string;
}

export interface RegraClassificacaoOut {
  id: string;
  titular_pix_padrao: string;
  orcamento_linha_id: string | null;
  categoria_id: string | null;
  projeto_id: string | null;
  empresa_id: string | null;
  confianca_base: number;
  uso_count: number;
  ativa: boolean;
  ultima_utilizacao: string | null;
}

export interface AdiantamentoOut {
  id: string;
  prestador_id: string;
  valor_bruto_solicitado: number;
  percentual_desconto: number;
  valor_liquido_pago: number;
  receita_financeira: number;
  data_pagamento: string;
  status: "ABERTO" | "COMPENSADO_PARCIAL" | "COMPENSADO_TOTAL" | "BAIXADO_MANUAL";
  compensado_em_registro_pp_id: string | null;
}

export interface PrestadorLinha {
  nome: string;
  valor_pp: number;
  valor_pago: number;
  datas_pix: string[];
  status: "PAGO" | "PARCIAL" | "PENDENTE" | "SEM_MOVIMENTO";
}

export interface ContratoCompetenciaOut {
  contrato_id: string;
  nome_contrato: string;
  competencia: string;
  total_devido: number;
  total_pago: number;
  percentual_pago: number;
  receita_prevista: number | null;
  margem_projetada: number | null;
  prestadores: PrestadorLinha[];
}

export interface KPIs {
  saldo_inicial: number;
  saidas_mes: number;
  previsto_a_pagar: number;
  saldo_atual: number;
}

export interface BarraPxR {
  categoria: string;
  previsto: number;
  realizado: number;
  pct: number;
}

export interface Alerta {
  tipo: "NAO_CONCILIADO" | "VENCIDO" | "PAGO_A_MAIOR" | "ESTORNO";
  mensagem: string;
  ref_id: string | null;
  ref_tipo: string | null;
}

export interface DashboardResponse {
  competencia: string;
  empresa_filtro: string;
  kpis: KPIs;
  saidas_por_natureza: Record<string, number>;
  previsto_x_realizado: BarraPxR[];
  alertas: Alerta[];
}
```

- [ ] **Step 3: Criar os 8 módulos em `frontend/lib/api/`** — cada um encapsulando fetches para um router. Exemplo para `catalogos.ts`:

```typescript
// frontend/lib/api/catalogos.ts
import { apiClient } from "@/lib/api";
import { EmpresaOut, CategoriaOut, ProjetoOut } from "@/types/v2";

export async function listarEmpresas(): Promise<EmpresaOut[]> {
  const { data } = await apiClient.get<EmpresaOut[]>("/empresas");
  return data;
}

export async function listarCategorias(): Promise<CategoriaOut[]> {
  const { data } = await apiClient.get<CategoriaOut[]>("/categorias");
  return data;
}

export async function listarProjetos(): Promise<ProjetoOut[]> {
  const { data } = await apiClient.get<ProjetoOut[]>("/projetos");
  return data;
}

export async function criarProjeto(payload: { codigo: string; descricao?: string; empresa_id: string }): Promise<ProjetoOut> {
  const { data } = await apiClient.post<ProjetoOut>("/projetos", payload);
  return data;
}

export async function deletarProjeto(id: string): Promise<void> {
  await apiClient.delete(`/projetos/${id}`);
}
```

Fazer equivalente para os outros 7 routers. Para uploads de arquivo usar `FormData` com `multipart/form-data`.

- [ ] **Step 4: Smoke test de compilação**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro/frontend
npm run build
```

Espera-se: build sem erros de TypeScript. Se houver warnings do Next, OK.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api/ frontend/types/v2.ts frontend/lib/api.ts
git commit -m "feat(frontend): api client v2 + types TypeScript para os 8 recursos novos"
```

---

### Task 4.2: Shell autenticado (layout + topbar + nav + filtros globais)

**Files:**
- Create: `frontend/app/(authed)/layout.tsx`
- Create: `frontend/components/layout/topbar.tsx`, `nav.tsx`, `filter-empresa.tsx`, `filter-competencia.tsx`
- Create: `frontend/lib/filters-context.tsx`
- Modify: `frontend/app/page.tsx` — será substituído por home dashboard (mover para `(authed)/page.tsx`)
- Modify: `frontend/middleware.ts` — redirect para `/` em vez de `/rodadas` após login

- [ ] **Step 1: Criar `frontend/lib/filters-context.tsx`**

```tsx
"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { EmpresaCodigo } from "@/types/v2";

interface FiltersContextType {
  empresa: EmpresaCodigo;
  setEmpresa: (e: EmpresaCodigo) => void;
  competencia: string;
  setCompetencia: (c: string) => void;
}

const FiltersContext = createContext<FiltersContextType | null>(null);

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [empresa, setEmpresa] = useState<EmpresaCodigo>("SPM");
  const [competencia, setCompetencia] = useState<string>(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });

  useEffect(() => {
    const savedE = localStorage.getItem("spm_filter_empresa");
    if (savedE === "SPM" || savedE === "FD" || savedE === "TODAS") setEmpresa(savedE);
    const savedC = localStorage.getItem("spm_filter_competencia");
    if (savedC && /^\d{4}-\d{2}$/.test(savedC)) setCompetencia(savedC);
  }, []);

  useEffect(() => {
    localStorage.setItem("spm_filter_empresa", empresa);
  }, [empresa]);
  useEffect(() => {
    localStorage.setItem("spm_filter_competencia", competencia);
  }, [competencia]);

  return (
    <FiltersContext.Provider value={{ empresa, setEmpresa, competencia, setCompetencia }}>
      {children}
    </FiltersContext.Provider>
  );
}

export function useFilters() {
  const ctx = useContext(FiltersContext);
  if (!ctx) throw new Error("useFilters fora do FiltersProvider");
  return ctx;
}
```

- [ ] **Step 2: Criar componentes de layout**

```tsx
// frontend/components/layout/topbar.tsx
"use client";
import { FilterEmpresa } from "./filter-empresa";
import { FilterCompetencia } from "./filter-competencia";

export function Topbar() {
  return (
    <header className="h-12 bg-slate-900 text-white px-4 flex items-center justify-between text-sm">
      <div className="font-semibold tracking-wide">⚕ SPM Financeiro</div>
      <div className="flex gap-2 items-center">
        <FilterEmpresa />
        <FilterCompetencia />
        {/* Perfil do usuário — por agora apenas "Hugo" */}
        <span className="text-xs text-slate-300">Hugo</span>
      </div>
    </header>
  );
}
```

```tsx
// frontend/components/layout/nav.tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/conciliacao", label: "Conciliação" },
  { href: "/contratos", label: "Contratos" },
  { href: "/rodadas", label: "Rodadas PP" },
  { href: "/orcamento", label: "Orçamento" },
  { href: "/adiantamentos", label: "Adiantamentos" },
  { href: "/extratos", label: "Extratos" },
  { href: "/cadastros", label: "Cadastros" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="h-10 bg-slate-800 text-slate-300 px-4 flex gap-1 text-sm overflow-x-auto">
      {ITEMS.map((it) => {
        const active = pathname === it.href || (it.href !== "/" && pathname.startsWith(it.href));
        return (
          <Link
            key={it.href}
            href={it.href}
            className={cn(
              "px-3 py-2 whitespace-nowrap border-b-2 border-transparent",
              active && "text-white font-medium border-blue-500 bg-slate-900"
            )}
          >
            {it.label}
          </Link>
        );
      })}
    </nav>
  );
}
```

```tsx
// frontend/components/layout/filter-empresa.tsx
"use client";
import { useFilters } from "@/lib/filters-context";
import { EmpresaCodigo } from "@/types/v2";

export function FilterEmpresa() {
  const { empresa, setEmpresa } = useFilters();
  return (
    <select
      value={empresa}
      onChange={(e) => setEmpresa(e.target.value as EmpresaCodigo)}
      className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs"
    >
      <option value="SPM">SPM</option>
      <option value="FD">FD</option>
      <option value="TODAS">SPM+FD</option>
    </select>
  );
}
```

```tsx
// frontend/components/layout/filter-competencia.tsx
"use client";
import { useFilters } from "@/lib/filters-context";

export function FilterCompetencia() {
  const { competencia, setCompetencia } = useFilters();
  return (
    <input
      type="month"
      value={competencia}
      onChange={(e) => setCompetencia(e.target.value)}
      className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs"
    />
  );
}
```

- [ ] **Step 3: Criar `frontend/app/(authed)/layout.tsx`**

```tsx
// frontend/app/(authed)/layout.tsx
import { Topbar } from "@/components/layout/topbar";
import { Nav } from "@/components/layout/nav";
import { FiltersProvider } from "@/lib/filters-context";

export default function AuthedLayout({ children }: { children: React.ReactNode }) {
  return (
    <FiltersProvider>
      <Topbar />
      <Nav />
      <main className="flex-1 overflow-auto bg-slate-50">{children}</main>
    </FiltersProvider>
  );
}
```

- [ ] **Step 4: Mover `/rodadas` para dentro do grupo `(authed)`**

O grupo `(authed)` não afeta URL. Criar `frontend/app/(authed)/rodadas/page.tsx` se a intenção for que o layout se aplique à rota `/rodadas`, OU mover `frontend/app/rodadas/` para `frontend/app/(authed)/rodadas/`. **Preferir mover** para manter uma raiz (authed) consistente.

- [ ] **Step 5: Ajustar middleware**

Em `middleware.ts`, trocar o redirect após login bem-sucedido de `/rodadas` para `/`:

```typescript
if (hasToken && pathname === "/login") {
  const url = req.nextUrl.clone();
  url.pathname = "/";
  return NextResponse.redirect(url);
}
```

- [ ] **Step 6: Criar placeholder `frontend/app/(authed)/page.tsx`** (será substituído por dashboard na Task 4.3):

```tsx
export default function Page() {
  return <div className="p-6">Dashboard — a implementar na Task 4.3</div>;
}
```

- [ ] **Step 7: Build + dev**

```bash
npm run build
npm run dev
```

Abrir navegador em `http://localhost:3000/` com usuário autenticado — deve ver topbar + nav + placeholder da home. Testar nav entre /rodadas, /login (deslogar), /.

- [ ] **Step 8: Commit**

```bash
git add frontend/app/(authed)/ frontend/components/layout/ frontend/lib/filters-context.tsx frontend/middleware.ts
git commit -m "feat(frontend): shell autenticado + topbar + nav + filtros globais (empresa/competencia)"
```

---

## M4-B — 7 telas (7 tasks)

### Task 4.3: Tela Dashboard (/)

**Files:**
- Modify/Create: `frontend/app/(authed)/page.tsx`
- Create: `frontend/components/dashboard/kpis-grid.tsx`, `donut-naturezas.tsx`, `barras-pxr.tsx`, `alertas-list.tsx`

Seguindo o mockup `.superpowers/brainstorm/3056-1776662200/content/dashboard-contratos.html`:
- 4 KPIs no topo (Saldo inicial, Saídas mês, Previsto a pagar, Saldo atual)
- Donut "Saídas por natureza" + legenda
- Barras "Previsto × Realizado" por categoria
- Lista de alertas (com links pra telas destino)

Lógica:
- `useFilters()` para obter `empresa` + `competencia`
- `useEffect` + `fetchDashboard(competencia, empresa)` ao montar e quando filtros mudam
- Loading state + error handling (toast via sonner)

Código das funcões de renderização:
- `kpis-grid.tsx`: 4 cards com `bg-white border rounded-lg p-4`, label uppercase pequeno + value grande tabular-nums
- `donut-naturezas.tsx`: SVG viewBox 42x42, um `<circle>` por natureza com `stroke-dasharray`
- `barras-pxr.tsx`: grid `grid-template-columns: 110px 1fr 90px` com barra + %
- `alertas-list.tsx`: cada alerta com borda esquerda colorida (cinza/amarelo/vermelho)

Use Tailwind v4 syntax (não v3). Classes utility padrão.

- [ ] **Step 1: Criar componentes acima**
- [ ] **Step 2: `(authed)/page.tsx`** monta todos
- [ ] **Step 3: Rodar `npm run dev` + navegar + validar visualmente**
- [ ] **Step 4: Commit**

```bash
git commit -am "feat(frontend): tela Dashboard — KPIs + donut + previsto x realizado + alertas"
```

---

### Task 4.4: Tela Conciliação (/conciliacao) — A CRÍTICA

**Files:**
- Create: `frontend/app/(authed)/conciliacao/page.tsx`
- Create: `frontend/components/conciliacao/two-panel.tsx`, `row-transacao.tsx`, `row-orcamento.tsx`

Seguindo o mockup `conciliacao-v1.html`:
- 2 colunas: transações não conciliadas (esq) × orçamento pendente (dir)
- Cada linha de transação com badge de origem (REGRA verde / SIMILARIDADE amarelo / VALOR cinza) + %confiança
- Footer com botão **"Confirmar TODOS os sugeridos"** (aplica todos os matches de `origem=REGRA` em lote) + "Casar fracionado"
- Cor-código nas linhas: verde (sugestão regra), amarelo (similaridade), cinza (valor), branco (sem sugestão)

Lógica:
1. Escolher orçamento (via filtro competência + empresa) — carregar lista e pegar o `status=VALIDADO` ou `RASCUNHO` da competência atual
2. `fetchSugestoes(orcamento_id)` — traz transações × linhas pareadas
3. Renderizar 2 colunas mostrando as pares sugeridas (transação vs linha de orçamento)
4. Seleção múltipla via checkbox — ao clicar "Confirmar selecionadas", faz `POST /conciliacoes` para cada
5. "Confirmar TODOS os sugeridos" — dispara em lote as sugestões de origem=REGRA (alta confiança)
6. Desfazer: botão de reverter uma conciliação (chama DELETE)

Código-base:

```tsx
// frontend/app/(authed)/conciliacao/page.tsx
"use client";
import { useEffect, useState } from "react";
import { useFilters } from "@/lib/filters-context";
import { listarOrcamentos } from "@/lib/api/orcamento";
import { fetchSugestoes, aplicarConciliacao } from "@/lib/api/conciliacao";
import { toast } from "sonner";
import type { SugestaoOut } from "@/types/v2";

export default function ConciliacaoPage() {
  const { empresa, competencia } = useFilters();
  const [orcamentoId, setOrcamentoId] = useState<string | null>(null);
  const [sugestoes, setSugestoes] = useState<SugestaoOut[]>([]);
  const [selecionadas, setSelecionadas] = useState<Set<string>>(new Set()); // chave: tx_id+linha_id
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listarOrcamentos({ empresa_codigo: empresa, competencia }).then((lista) => {
      if (!lista.length) { setLoading(false); return; }
      const orc = lista[0];
      setOrcamentoId(orc.id);
      return fetchSugestoes(orc.id).then((sugs) => setSugestoes(sugs));
    }).finally(() => setLoading(false));
  }, [empresa, competencia]);

  async function confirmarTodosSugeridosRegra() {
    const de_regra = sugestoes.filter(s => s.origem === "REGRA");
    if (!de_regra.length) { toast.info("Nenhuma sugestão de regra salva"); return; }
    let ok = 0;
    for (const s of de_regra) {
      try {
        await aplicarConciliacao({
          transacao_id: s.transacao_id,
          orcamento_linha_id: s.orcamento_linha_id,
          valor_aplicado: s.valor_aplicado,
          confianca: s.confianca,
          origem: s.origem,
        });
        ok++;
      } catch (e) {
        console.error(e);
      }
    }
    toast.success(`${ok} conciliações aplicadas`);
    // Recarrega
    if (orcamentoId) setSugestoes(await fetchSugestoes(orcamentoId));
  }

  if (loading) return <div className="p-6">Carregando...</div>;
  if (!orcamentoId) return <div className="p-6">Nenhum orçamento encontrado para a competência selecionada. Faça upload primeiro.</div>;

  // Renderiza grid 2 colunas via <TwoPanel sugestoes={sugestoes} ... />
  // (componente com lógica visual cor-código + checkboxes + botões footer)
  ...
}
```

- [ ] **Step 1-4: Implementar 2-panel + commits**

```bash
git commit -am "feat(frontend): tela Conciliacao — 2 colunas + sugestao cascata + confirmar TODOS"
```

---

### Task 4.5: Tela Contratos × Competência (/contratos)

**Files:**
- Create: `frontend/app/(authed)/contratos/page.tsx` (lista)
- Create: `frontend/app/(authed)/contratos/[id]/[competencia]/page.tsx` (detalhe)
- Create: `frontend/components/contratos/contrato-card.tsx`

Lista:
- Cards empilhados, um por contrato×competência com barra de progresso % pago
- Receita prev / Despesa prev / Despesa real / Margem
- Click abre detalhe

Detalhe:
- Tabela de prestadores (Data PIX → Status)
- Total devido / total pago / percentual
- Gráfico barra linear

- [ ] Seguir mockup `dashboard-contratos.html` (parte de contratos)
- [ ] Commit: `feat(frontend): tela Contratos x Competencia — lista + detalhe DRE`

---

### Task 4.6: Tela Orçamento (/orcamento)

**Files:**
- Create: `frontend/app/(authed)/orcamento/page.tsx`
- Create: `frontend/components/orcamento/tabs-secoes.tsx`, `tabela-linhas.tsx`, `upload-xlsx-dialog.tsx`

Seguindo mockup `orcamento-v2.html`:
- Strip de meses no topo (Jan/Fev fechados, Mar/Abr validados, Mai rascunho)
- 6 abas por natureza (Despesas Fixas / Tributos / Variáveis-Salários / Comissões / Variáveis-Outros / Profissionais)
- Tabela com colunas: Razão Social · Categoria · Projeto · Empresa · Previsto · Pago · Saldo · **Data → Status** · Obs
- Botões: Upload XLSX (dialog) · Adicionar linha · Replicar para próximo mês

- [ ] Commit: `feat(frontend): tela Orcamento — strip meses + 6 abas + upload XLSX + replicacao`

---

### Task 4.7: Tela Adiantamentos (/adiantamentos)

**Files:**
- Create: `frontend/app/(authed)/adiantamentos/page.tsx`
- Create: `frontend/components/adiantamento/lista-tabela.tsx`, `compensar-dialog.tsx`

Lista de adiantamentos + filtros (status, prestador). Cada linha: prestador, valor bruto/líquido, desconto, data pagamento, **Data (compensação) → Status**. Modal "Compensar" permite selecionar `registro_pp_id` (dropdown filtrado por prestador_id + mes_competencia >= data_pagamento).

- [ ] Commit: `feat(frontend): tela Adiantamentos — lista + compensar manual via modal`

---

### Task 4.8: Tela Extratos (/extratos)

**Files:**
- Create: `frontend/app/(authed)/extratos/page.tsx`
- Create: `frontend/components/extrato/upload-dialog.tsx`

2 upload buttons (Unicred PDF + Bradesco OFX). Cada upload faz `POST /extratos/<tipo>/upload`. Mostra resultado (qtd transações + período).

Lista de transações recentes (últimos 30 dias) com filtros.

- [ ] Commit: `feat(frontend): tela Extratos — upload Unicred PDF + Bradesco OFX + lista`

---

### Task 4.9: Tela Cadastros (/cadastros)

**Files:**
- Create: `frontend/app/(authed)/cadastros/page.tsx`
- Create: `frontend/components/cadastros/tabs-entidades.tsx`

4 tabs: Projetos / Categorias / Contas Bancárias / Regras de Classificação. Cada tab com tabela CRUD básica.

- Projetos: criar (nome, empresa) / listar / desativar
- Categorias: listar (read-only nesta fase)
- Contas Bancárias: criar (banco, conta, finalidade) / listar
- Regras: listar + desativar (Tarefa 3.11 do Plano 2)

- [ ] Commit: `feat(frontend): tela Cadastros — 4 tabs (projetos, categorias, contas, regras)`

---

## M4-C — Finalização (2 tasks)

### Task 4.10: Ajustes na tela Rodadas PP existente

**Files:**
- Modify: `frontend/app/(authed)/rodadas/page.tsx` e subrotas
- Modify: `frontend/app/(authed)/rodadas/[id]/page.tsx`

- Adicionar banner no topo quando há adiantamentos abertos do prestador da rodada (fetch `/adiantamentos?status_filtro=ABERTO`)
- Link para `/adiantamentos` no banner

- [ ] Commit: `feat(frontend): rodadas PP — banner de adiantamentos abertos + link`

---

### Task 4.11: Smoke visual + documentação

- [ ] Rodar `npm run dev`, navegar por todas as 7 telas com dados reais do backend. Checklist:
  - [ ] Login funciona e redireciona para `/`
  - [ ] Dashboard renderiza sem erro (mesmo sem dados)
  - [ ] Conciliação lista sugestões do orçamento+extrato atuais
  - [ ] Contratos lista contratos do seed Bertioga, Iguape, etc.
  - [ ] Orçamento mostra as 6 abas
  - [ ] Adiantamentos lista (pode estar vazio)
  - [ ] Extratos — upload Unicred PDF funciona visualmente
  - [ ] Cadastros — 4 tabs funcionam
  - [ ] Filtro global de empresa + competência no topbar troca entre SPM/FD
  - [ ] Convenção Data→Status aplicada em todas as tabelas

- [ ] Atualizar `frontend/README.md` com instruções de local:
  ```
  npm install
  NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
  ```

- [ ] Commit final:
  ```bash
  git commit -am "chore: encerra Plano 3 M4 (UI) — frontend v2 completo em localhost

  7 telas + navegacao global + filtros globais + integracao com 8 routers.
  Deploy (M5+M6) fica para sessao separada.
  "
  ```

---

## Self-review

- [ ] Coverage spec §6: cada tela listada (Dashboard, Conciliação, Contratos, Rodadas PP, Orçamento, Adiantamentos, Extratos, Cadastros) implementada.
- [ ] Convenção Data→Status aplicada em **Orçamento**, **Adiantamentos**, **Contratos**, **Extratos**, **Rodadas PP** — todas que têm essas colunas.
- [ ] Filtros globais (empresa, competência) afetam Dashboard, Conciliação, Contratos e Orçamento coerentemente.
- [ ] Build `npm run build` sem erros TypeScript.
- [ ] Smoke manual: todas 7 telas navegáveis, sem 500/400.
- [ ] Nenhuma regressão em rodadas PP existente (testes backend continuam passando).

---

## Checklist de entrega (Plano 3 M4)

- [x] 11 tasks (2 fundação + 7 telas + 2 finalização)
- [x] 7 rotas `/*` completas + `(authed)` layout + middleware ajustado
- [x] API client completo para 8 routers
- [x] Filtros globais persistidos em localStorage
- [x] Mockups do brainstorm incorporados (Dashboard, Conciliação, Orçamento)
- [x] Botão "Confirmar TODOS sugeridos" operacional (o "mata-dor")

## Próximos passos após Plano 3 M4

**Plano 4 — Deploy + Go Live** (M5 + M6 do spec):
- Deploy backend Render, frontend Vercel
- Env vars de produção (Supabase, CORS, JWT)
- Dados reais (upload orçamento 04/26 real, Unicred PDF, rodada real)
- Primeiro ciclo mensal completo — Hugo opera fim a fim
