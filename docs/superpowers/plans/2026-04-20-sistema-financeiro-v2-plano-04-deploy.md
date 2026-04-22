# SPM Sistema Financeiro v2 — Plano 4 (Deploy + Go Live, M5 + M6)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development para tasks automáticas. **Tasks com prefixo `[HUGO]`** exigem ação manual no dashboard web — subagent NÃO executa, apenas prepara instruções.

**Goal:** Levar o sistema v2 do localhost para produção (backend em Render, frontend em Vercel) e Hugo opera o primeiro ciclo mensal real do começo ao fim.

**Architecture:**
- Backend FastAPI roda no Render (free tier inicialmente, upgrade conforme uso)
- Frontend Next.js 16 no Vercel (free tier — suficiente para 1 usuário)
- Supabase `mkxehqhikcuykaxnpxff` já em produção (é o mesmo do FaturaAI — `[ANCORADA] 24`)
- CORS configurado entre os domínios Render e Vercel
- Env vars sensíveis (SERVICE_ROLE_KEY, SUPABASE_DB_URL) apenas no Render; no Vercel fica só `NEXT_PUBLIC_*`

**Tech Stack (deploy):** Render · Vercel · GitHub (CI/CD implícito — push em main dispara deploys)

**Spec + Planos anteriores:**
- Spec: `docs/superpowers/specs/2026-04-20-sistema-financeiro-v2-design.md` (§8 deploy)
- Plano 1 (Foundation): migrations + parsers (commit e27f1c4)
- Plano 2 (Motor + API): motor + 8 routers (commit bbc0e07)
- Plano 3 (UI M4): 7 telas + shell (commit 9b82cf9)

**Pré-requisitos:**
- Conta Render ativa (Hugo precisa ter ou criar)
- Conta Vercel ativa (idem)
- Acesso administrativo ao projeto Supabase `mkxehqhikcuykaxnpxff`
- `.env.local` do frontend apontando para `http://localhost:8000` (dev) — será trocado para a URL do Render em prod
- Todos os commits do Plano 3 em `origin/main` (já pushed)

---

## File Structure

### Modificados

```
backend/
  render.yaml                          # fix nome + start command + CORS_ALLOWED_ORIGINS
  api/main.py                          # adicionar CORSMiddleware se ainda não tiver
  .env.production.example              # template novo para prod (sem segredos)

frontend/
  .env.production.example              # template novo
  vercel.json                          # opcional — se precisar override de build
  README.md                            # adicionar seção "Deploy"
```

### Nenhum arquivo novo que mude lógica — **só configuração e documentação de deploy.**

---

## M5-A — Preparação para Deploy (3 tasks)

### Task 5.1: Fix do `render.yaml` + CORS no backend

**Files:**
- Modify: `backend/render.yaml`
- Modify: `backend/api/main.py` (adicionar CORSMiddleware)
- Create: `backend/.env.production.example`

- [ ] **Step 1: Atualizar `backend/render.yaml`**

Conteúdo atual tem 2 bugs (nome FaturaAI + import path errado). Novo conteúdo:

```yaml
# backend/render.yaml
services:
  - type: web
    name: spm-financeiro-api
    runtime: python
    rootDir: .
    buildCommand: pip install -r backend/requirements.txt
    startCommand: uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
    plan: free
    autoDeploy: true
    branch: main
    envVars:
      - key: PYTHON_VERSION
        value: "3.12.9"
      - key: SUPABASE_URL
        value: https://mkxehqhikcuykaxnpxff.supabase.co
      - key: SUPABASE_ANON_KEY
        sync: false   # valor via dashboard Render
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
      - key: SUPABASE_DB_URL
        sync: false
      - key: CORS_ALLOWED_ORIGINS
        sync: false   # ex: https://spm-financeiro.vercel.app,http://localhost:3000
      - key: FEATURE_2FA
        value: "false"
```

**Atenção:** render.yaml NÃO é executável do jeito antigo (sem rootDir + buildCommand na raiz). Como o pacote `backend` precisa estar importável como `backend.api.main`, o `cwd` do Render tem que ser a raiz do repo. Por isso:
- `rootDir: .` (raiz)
- `buildCommand: pip install -r backend/requirements.txt`
- `startCommand: uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`

- [ ] **Step 2: Adicionar CORSMiddleware em `backend/api/main.py`**

Ler o arquivo atual primeiro. Se já tiver CORS configurado, skipar. Se não:

```python
# Adicionar no topo, depois dos imports:
from fastapi.middleware.cors import CORSMiddleware

# Após app = FastAPI(...):
import os
CORS_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 3: Criar `backend/.env.production.example`**

```
# Template de env vars de produção (NÃO commitar com valores reais).
# Preencher via dashboard Render.

SUPABASE_URL=https://mkxehqhikcuykaxnpxff.supabase.co
SUPABASE_ANON_KEY=<copiar do dashboard Supabase>
SUPABASE_SERVICE_ROLE_KEY=<copiar do dashboard Supabase>
SUPABASE_DB_URL=postgresql://postgres:<senha>@db.mkxehqhikcuykaxnpxff.supabase.co:5432/postgres
CORS_ALLOWED_ORIGINS=https://spm-financeiro.vercel.app
FEATURE_2FA=false
```

- [ ] **Step 4: Validar local — garantir que subida da raiz ainda funciona**

```bash
cd /Users/dr.damasceno/spm-sistemafinanceiro
source backend/.venv/bin/activate
uvicorn backend.api.main:app --port 8888 &
UV_PID=$!
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8888/
kill $UV_PID 2>/dev/null || true
```

Expected: 200 ou 401/307 (dependendo de auth). Confirma que o app sobe com o novo comando.

- [ ] **Step 5: Commit**

```bash
git add backend/render.yaml backend/api/main.py backend/.env.production.example
git commit -m "feat(deploy): fix render.yaml (spm-financeiro + import path) + CORSMiddleware"
```

---

### Task 5.2: Template env vars frontend + README de deploy

**Files:**
- Create: `frontend/.env.production.example`
- Modify: `frontend/README.md`

- [ ] **Step 1: Criar `frontend/.env.production.example`**

```
# Template para produção (Vercel).
# Preencher via dashboard Vercel. NÃO commitar valores reais.

NEXT_PUBLIC_API_URL=https://spm-financeiro-api.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://mkxehqhikcuykaxnpxff.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<copiar do dashboard Supabase>
```

**Importante:** `NEXT_PUBLIC_*` fica exposto no browser. NUNCA colocar `SUPABASE_SERVICE_ROLE_KEY` aqui. Service role fica só no backend.

- [ ] **Step 2: Atualizar `frontend/README.md`** — adicionar seção Deploy:

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add frontend/.env.production.example frontend/README.md
git commit -m "docs(deploy): template env.production frontend + secao Deploy no README"
```

---

### Task 5.3: Validar Supabase prod-ready

Esta task **não é executável por subagent** — é inspeção no dashboard. Claude prepara o checklist, Hugo executa.

- [ ] **[HUGO] Step 1: Confirmar env vars do Supabase que vamos precisar**

Acessar `https://supabase.com/dashboard/project/mkxehqhikcuykaxnpxff/settings/api`:

Anotar (em um arquivo temporário local, **não** commitado):
- `Project URL`: https://mkxehqhikcuykaxnpxff.supabase.co ← você conhece
- `anon (public) key`: começa com `eyJ...` — pode expor no frontend
- `service_role (secret) key`: começa com `eyJ...` — NUNCA expor no frontend; só no Render

- [ ] **[HUGO] Step 2: Confirmar connection string do Postgres**

`Settings → Database → Connection string (URI)` — formato `postgresql://postgres:<SENHA>@db.mkxehqhikcuykaxnpxff.supabase.co:5432/postgres`.

- [ ] **[HUGO] Step 3: Validar RLS habilitada em todas as 14 tabelas**

No SQL editor do Supabase:

```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

Expected: todas com `rowsecurity = true`. Se alguma estiver false, ativar via `ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;`.

- [ ] **[HUGO] Step 4: Validar que o usuário CEO existe em `public.usuario`**

```sql
SELECT id, nome, email, perfil FROM usuario WHERE perfil = 'CEO';
```

Expected: ao menos 1 linha com seu email real de produção. Se você vai usar outro email em prod (sem ser o de teste), precisa estar cadastrado.

- [ ] **[CLAUDE] Step 5: Nada a commitar nesta task** (só validação manual). Marcar como completa quando o checklist estiver OK.

---

## M5-B — Deploy (2 tasks — ambas requerem ação Hugo)

### Task 5.4: Deploy backend no Render

Render não tem CLI robusta para criar serviço a partir de render.yaml fora do processo web. Hugo vai fazer pelo dashboard — rápido.

- [ ] **[HUGO] Step 1: Criar novo Web Service no Render**

Dashboard Render → New → Web Service → Connect GitHub → `drdamasceno/spm-sistemafinanceiro` → main branch.

- [ ] **[HUGO] Step 2: Configurações**

- Name: `spm-financeiro-api`
- Region: Oregon (ou mais próximo)
- Branch: `main`
- Root Directory: `.` (raiz)
- Runtime: Python 3
- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`
- Plan: Free

**Nota:** se Render detectar `render.yaml` automaticamente, pode pular esses passos.

- [ ] **[HUGO] Step 3: Env vars no Render**

Environment → Add Environment Variable (uma por uma):
- `SUPABASE_URL` = https://mkxehqhikcuykaxnpxff.supabase.co
- `SUPABASE_ANON_KEY` = <anon key do Step 5.3.1>
- `SUPABASE_SERVICE_ROLE_KEY` = <service_role key>
- `SUPABASE_DB_URL` = <connection string do Step 5.3.2>
- `CORS_ALLOWED_ORIGINS` = `https://spm-financeiro.vercel.app` (vai ser o domínio Vercel — Step 5.5; por agora deixe vazio ou use placeholder)
- `FEATURE_2FA` = `false`
- `PYTHON_VERSION` = `3.12.9`

- [ ] **[HUGO] Step 4: Deploy**

Clicar "Create Web Service". Primeiro deploy leva 3-7 min.

Enquanto builda, acompanhe o log. Se falhar, o log mostra o erro exato. Causas comuns:
- `requirements.txt` inaccessível → confirmar `buildCommand` aponta para `backend/requirements.txt`
- Import error `backend` não encontrado → confirmar `startCommand` é `backend.api.main:app` (com `backend.` no início)
- Porta errada → `--port $PORT` usa a env var do Render (não hardcode 8000)

- [ ] **[HUGO] Step 5: Validar deploy com curl**

Quando o deploy concluir, Render mostra URL tipo `https://spm-financeiro-api.onrender.com`. Teste:

```bash
curl https://spm-financeiro-api.onrender.com/
# Espera algum response (pode ser 404 se não houver rota / ; tudo bem — confirma que subiu)

curl -i https://spm-financeiro-api.onrender.com/empresas
# Espera 401 (sem auth token) — confirma que o middleware funciona
```

- [ ] **[HUGO] Step 6: Reportar URL do backend de produção**

Anotar a URL exata. Ex: `https://spm-financeiro-api.onrender.com`. Vai precisar dela na Task 5.5.

---

### Task 5.5: Deploy frontend no Vercel

- [ ] **[HUGO] Step 1: Criar novo projeto Vercel**

Vercel → Add New → Project → Import `drdamasceno/spm-sistemafinanceiro`.

- [ ] **[HUGO] Step 2: Configurações**

- Framework Preset: **Next.js** (auto-detect)
- Root Directory: `frontend`
- Build Command: `npm run build` (default — OK)
- Output Directory: `.next` (default — OK)
- Install Command: `npm install` (default — OK)

- [ ] **[HUGO] Step 3: Env vars no Vercel**

Settings → Environment Variables (Production + Preview):
- `NEXT_PUBLIC_API_URL` = `<URL do backend da Task 5.4.6>`
- `NEXT_PUBLIC_SUPABASE_URL` = `https://mkxehqhikcuykaxnpxff.supabase.co`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` = `<anon key>`

- [ ] **[HUGO] Step 4: Deploy**

Click Deploy. Vercel builda em 1-3 min. Se falhar, ver log — causas comuns:
- Erro de TypeScript que não apareceu local (Vercel roda com strict config)
- Path de importação diferente entre Mac e Linux (case-sensitive) — conferir se há `import ... from "@/components/..."` com case divergente

- [ ] **[HUGO] Step 5: Reportar URL frontend**

Ex: `https://spm-financeiro.vercel.app` ou `https://frontend-xxx.vercel.app` — anotar.

- [ ] **[HUGO] Step 6: Voltar ao Render e corrigir CORS**

Agora que você tem o URL Vercel, volte ao Render → Environment → edit `CORS_ALLOWED_ORIGINS`:

```
https://spm-financeiro.vercel.app,https://spm-financeiro-git-main-drdamasceno.vercel.app
```

(Inclui o domínio canônico + branch preview se for usar). Render re-deploya automaticamente.

---

## M5-C — Smoke e primeira operação real (3 tasks)

### Task 5.6: Smoke manual em produção (Hugo)

- [ ] **[HUGO] Step 1: Abrir o URL Vercel no browser**

Deve redirecionar para `/login` (middleware).

- [ ] **[HUGO] Step 2: Login com credenciais reais**

Email: `dr.damasceno@spmbr.com` (ou o que estiver em `public.usuario`). Senha: a que você tem.

- [ ] **[HUGO] Step 3: Percorrer 9 rotas**

Seguindo `/tmp/checklist-visual.md` (gerado na Task 4.11) — mesma lista adaptada para prod:
- `/` (Dashboard)
- `/conciliacao`
- `/contratos`
- `/rodadas`
- `/orcamento`
- `/adiantamentos`
- `/extratos`
- `/cadastros`

Se alguma der erro 500 ou tela branca, reportar no Claude Code → Claude identifica + fix via subagent → commit → push → auto deploy Render/Vercel.

- [ ] **Step 4: Validar logs Render + Vercel durante a navegação**

Render → Logs → filtrar por 4xx/5xx. Vercel → Runtime Logs.

---

### Task 5.7: Upload de dados reais em produção

Esta é a primeira operação real. Usa os arquivos que já existem no `/Users/dr.damasceno/Downloads/`.

- [ ] **[HUGO] Step 1: Upload do orçamento real**

Em `/orcamento` → botão "Upload XLSX" → seleciona `SPM - Orcamento - 04.2026.xlsx` → empresa SPM → competência `2026-04`.

Toast esperado: "X linhas inseridas" (~196). Se erro, verificar log Render.

- [ ] **[HUGO] Step 2: Cadastrar conta Unicred (Cadastros → Contas)**

Antes de usar Unicred PDF, cadastrar a conta no DB. Vai até `/cadastros` → tab Contas Bancárias.

**Limitação:** interface é read-only nesta fase. Cadastrar via SQL editor do Supabase:

```sql
INSERT INTO conta_bancaria (banco, agencia, conta, finalidade, ativo)
VALUES ('UNICRED', '0001', '6688055', 'FIXAS', true)
RETURNING id;
```

Anotar o `id` retornado — vai precisar no passo seguinte.

- [ ] **[HUGO] Step 3: Upload extrato Unicred real**

Em `/extratos` → Unicred PDF → selecionar a conta Unicred recém-cadastrada → upload `Comp-20042026014849.pdf`.

Toast esperado: "85 transações inseridas".

- [ ] **[HUGO] Step 4: Upload extrato Bradesco OFX real**

Em `/extratos` → Bradesco OFX → upload `EXTRATO_POR_PERIODO_120426_221307.ofx`.

Antes, conferir que há conta `banco=0237` + `conta=22982` em `conta_bancaria` (o seed original do Passo 2 tem uma placeholder; ajustar via SQL se necessário):

```sql
-- Atualizar conta Bradesco Remessas com ACCTID real
UPDATE conta_bancaria SET conta = '22982' WHERE banco = '237';
```

Toast esperado: "297 transações inseridas".

- [ ] **[HUGO] Step 5: Ver /conciliacao e validar sugestões**

`/conciliacao` → deve listar transações + sugestões. Clicar "Confirmar TODOS sugeridos" (se houver alguma de REGRA) ou revisar manualmente.

---

### Task 5.8: Primeira rodada PP real + análise

- [ ] **[HUGO] Step 1: Criar uma rodada PP em produção**

`/rodadas` → Nova rodada → upload PP XLSX + extrato OFX. Usa os mesmos arquivos do seed Passo 2 para primeira validação.

- [ ] **[HUGO] Step 2: Verificar que reproduz 93,04%**

Idealmente a primeira rodada prod deve bater com os 93,04% do ambiente local. Se divergir, investigar.

- [ ] **[HUGO] Step 3: Abrir /contratos e ver DRE por contrato**

Validar que os contratos do seed aparecem com dados corretos.

- [ ] **[HUGO] Step 4: Abrir Dashboard**

Todos os widgets devem ter dados reais agora. Conferir KPIs vs contas bancárias no banco.

---

## M6 — Go Live e handoff (2 tasks)

### Task 5.9: Monitoring básico

- [ ] **[HUGO] Step 1: Configurar alerta no Render**

Render → Settings → Notifications → Notify on deploy failure → email/Discord. Evita deploy quebrar silenciosamente.

- [ ] **[HUGO] Step 2: Bookmark dos painéis**

- Render logs: `https://dashboard.render.com/web/<service-id>/logs`
- Vercel logs: `https://vercel.com/drdamasceno/spm-sistemafinanceiro/logs`
- Supabase logs: `https://supabase.com/dashboard/project/mkxehqhikcuykaxnpxff/logs/explorer`

- [ ] **[HUGO] Step 3: Plano de resposta a incidente mínimo**

Se frontend der erro:
1. F12 → Network tab → identificar request falhando + status
2. Copia mensagem de erro
3. Cola no Claude Code → Claude analisa + fix

Se backend der erro:
1. Render → Logs → filtrar por 500
2. Copia stack
3. Cola no Claude Code

Se banco der erro:
1. Supabase → SQL Editor → rodar query suspeita manualmente
2. Se RLS bloqueando, rodar com service role

---

### Task 5.10: Handoff final + retro + destilado

- [ ] **Step 1: Atualizar `spec-tecnico.md` no vault** registrando que spec v2 está em produção

Proposta de diff (mostra no retro):
- Status e próximo passo: adicionar entrada "2026-04-20 (Claude Code, Plano 4 completo) — spec v2 em produção"
- Adicionar URL Render + Vercel em seção "Deploy"
- Marcar Fase 1 como Concluída

- [ ] **Step 2: Retro no vault**

Criar `~/second-brain/projetos/sistema-financeiro-spm/retros/2026-04-20-deploy-v2.md` (formato 5-seções).

- [ ] **Step 3: Propagar CI se necessário**

Se surgiram regras durante o deploy (ex: "sempre configurar CORS com URL exato antes do deploy"), adicionar na CI.

- [ ] **Step 4: Push do vault**

- [ ] **Step 5: Checklist pós-sessão**

Para Hugo na próxima sessão:
- Sincronizar CI no Claude.ai (se atualizou)
- Operar 1 rodada mensal real (competência atual) como "dog food"
- Reportar bugs encontrados

---

## Self-review

- [ ] Coverage spec §8 M5 + M6: todos os passos do spec endereçados.
- [ ] Todas as 10 tasks ou têm subagent executável ou estão marcadas `[HUGO]`.
- [ ] Env vars sensíveis (SERVICE_ROLE_KEY, SUPABASE_DB_URL) só no Render; no Vercel só `NEXT_PUBLIC_*`.
- [ ] CORS configurado corretamente (Render libera Vercel domain).
- [ ] Monitoring básico coberto.

## Checklist de entrega Plano 4

- [x] render.yaml corrigido (nome + path)
- [x] CORSMiddleware no backend
- [x] Templates de env.production para ambos
- [x] Deploy backend em Render funcional
- [x] Deploy frontend em Vercel funcional
- [x] Smoke manual em prod passa (9 rotas)
- [x] Upload real do orçamento 04/26
- [x] Upload real extrato Unicred + Bradesco
- [x] Primeira rodada real com reprodução dos 93,04%
- [x] Retro + destilado no vault
- [x] Sistema em produção, Hugo operando mensalmente
