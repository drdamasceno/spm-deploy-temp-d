# SPM — Sistema Financeiro — Frontend

UI do sistema financeiro SPM (conciliacao + orcamento + contratos + dashboard).
Next.js 16 + React 19 + TypeScript + Tailwind v4 + shadcn/ui.

## Stack

- Next.js 16 (App Router, sem `src/`, sem ESLint)
- React 19 + TypeScript
- Tailwind CSS v4 + shadcn/ui (tema `neutral`)
- `axios` para HTTP + interceptor de refresh
- `react-hook-form` + `zod` para formularios
- `js-cookie` para tokens (compatibilidade com middleware edge)
- `sonner` para toasts
- `date-fns`, `lucide-react`, `recharts`

## Variaveis de ambiente

Copie `.env.example` para `.env.local` e preencha:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://mkxehqhikcuykaxnpxff.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key do dashboard Supabase>
```

`.env.local` esta no `.gitignore` — nao commitar credenciais.

## Rodar (dev)

Dependencia: backend FastAPI em `localhost:8000`.

```bash
# Terminal 1 — backend
cd ~/spm-sistemafinanceiro
source backend/.venv/bin/activate
uvicorn backend.api.main:app --port 8000

# Terminal 2 — frontend
cd ~/spm-sistemafinanceiro/frontend
npm run dev
```

Abrir http://localhost:3000.

## Build

```bash
npm run build
npm run start
```

## Fluxo de autenticacao

- Tokens (`spm_access_token`, `spm_refresh_token`) em cookies nao-httpOnly.
- `middleware.ts` redireciona para `/login` se `spm_access_token` ausente.
- Interceptor de response em `lib/api.ts`: em 401 tenta `POST /auth/refresh`
  uma vez; se falhar, limpa cookies e redireciona para `/login`.

## Rotas

Shell autenticado com topbar (filtros globais Empresa + Competencia) e nav horizontal
com 8 secoes. Todas as rotas authed sao protegidas pelo `middleware.ts`.

- `/login` — autenticacao Supabase (email + senha)
- `/` — Dashboard "Pra onde foi o dinheiro" (4 KPIs, donut natureza, barras
  previsto x realizado, alertas)
- `/conciliacao` — Conciliacao extrato <-> orcamento (2 colunas + cascata de sugestoes)
- `/contratos` — Contratos x Competencia (DRE por contrato: receita, despesa, margem, %)
- `/contratos/[id]/[competencia]` — detalhe do contrato (tabela de prestadores)
- `/rodadas` — Rodadas PP (Passo 5a); banner de adiantamentos abertos
- `/rodadas/nova`, `/rodadas/[id]` — criar / detalhar rodada
- `/orcamento` — Orcamento mensal (strip de meses + 6 abas + upload XLSX + replicacao)
- `/adiantamentos` — Lista + modal de compensacao manual
- `/extratos` — Upload Unicred PDF + Bradesco OFX
- `/cadastros` — 4 tabs (Projetos CRUD, Categorias read-only, Contas Bancarias read-only,
  Regras toggle)

## Estrutura

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                     Dashboard
│   ├── login/page.tsx
│   └── (authed)/                    Shell autenticado com topbar + nav
│       ├── layout.tsx
│       ├── conciliacao/page.tsx
│       ├── contratos/
│       │   ├── page.tsx
│       │   └── [id]/[competencia]/page.tsx
│       ├── rodadas/
│       ├── orcamento/page.tsx
│       ├── adiantamentos/page.tsx
│       ├── extratos/page.tsx
│       └── cadastros/page.tsx
├── components/
│   ├── ui/                          shadcn/ui (auto)
│   ├── layout/                      Topbar, Nav, filtros globais
│   ├── dashboard/, conciliacao/, contratos/, orcamento/,
│   │   adiantamentos/, extratos/, cadastros/, rodada/
├── lib/
│   ├── api.ts                       axios + interceptors + funcoes tipadas
│   ├── auth.ts, format.ts, types.ts, utils.ts
│   └── filters.ts                   filtros globais (empresa / competencia)
└── middleware.ts
```

## Convencoes

- **Data -> Status**: em qualquer tabela com ambas as colunas, Status vem depois de Data.
- **Filtros globais** (empresa, competencia) no topbar, persistidos em localStorage.
- **Tabular nums** em todos os valores monetarios (`font-variant-numeric: tabular-nums`).
- **Shadcn neutral** — prioriza legibilidade.

## Decisoes

- **Filtros client-side na tabela** — paginacao server-side (50/pagina),
  filtros so na pagina atual. Ajustar se volume crescer.
- **Upload + conciliar em 2 chamadas** — endpoints separados no backend;
  UI orquestra com feedback intermediario.
- **Shell authed com route group `(authed)`** — topbar + nav centralizados,
  sem duplicacao em cada pagina.

## Deploy (Vercel)

Pré-requisitos: conta Vercel + repo conectado.

1. Em Vercel → Import Project → selecionar `spm-sistemafinanceiro` → root directory `frontend`
2. Framework: Next.js (auto-detectado)
3. Build Command: `npm run build` (default)
4. Output Directory: `.next` (default)
5. Env vars (Settings → Environment Variables):
   - `NEXT_PUBLIC_API_URL` = URL do backend no Render (ex: https://spm-financeiro-api.onrender.com)
   - `NEXT_PUBLIC_SUPABASE_URL` = https://mkxehqhikcuykaxnpxff.supabase.co
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = anon key (pega no Supabase dashboard)
6. Deploy. A cada push em main o Vercel refaz o deploy.
