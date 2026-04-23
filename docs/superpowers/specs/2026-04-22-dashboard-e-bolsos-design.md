# Track B — Dashboard refinado e separação de bolsos: Design

**Data:** 2026-04-22
**Status:** Spec aprovado em brainstorm · aguardando revisão escrita
**Escopo anterior coberto:** Track C (contratos por cidade) · Track D (saldos/aplicações) · Opção C (PAGAMENTO_INTRAGRUPO)

---

## 1. Visão geral

Resolve dois problemas conectados:

**Problema 1 — "Onde está o dinheiro?"** O Dashboard atual tem `saldo_inicial=0` hardcoded, `previsto_a_pagar=0` não calculado, e `saldo_atual` divergente da Liquidez Total. Gráficos de breakdown (donut por natureza, barras previsto × realizado) ocupam metade da home competindo com os KPIs essenciais. Faltam visibilidade de compromissos em aberto com profissionais, recebíveis em atraso, receita financeira, e tendência histórica.

**Problema 2 — Bolsos financeiros misturados.** O orçamento SPM hoje mistura quatro naturezas de pagamento que passam pelo caixa: operação SPM, serviços prestados por FD (CLTs staff + CLTs produção), despesas pessoais de Hugo e investimentos imobiliários pessoais. O sistema não consegue responder "quanto saiu por bolso este mês" nem evitar duplicidade entre PIX consolidado SPM→FD e registros individuais dos CLTs FD que também aparecem no PP.

**Solução:**
- Home enxuta com 3 zonas cognitivas (onde está agora · o que aconteceu este mês · para onde está indo)
- Breakdown detalhado migra para subpáginas acessíveis por clique
- Modelo de dados ganha dimensão `bolso` ortogonal à natureza, vínculo prestador ↔ PJ empregadora, split de transação, saldo diário do caixa e rendimento explícito em aplicações
- Regra anti-duplicidade na conciliação: PIX intragrupo concilia em lote contra linhas com `empresa_pagadora`, CLTs FD saem do pool individual

**Fora de escopo** (explícito): camada jurídico-contábil (contratos, mútuo, política de distribuição de lucros) — documentada em `~/second-brain/dominios/spm/recomendacoes-juridico-contabeis.md`, executada por advogado + Fortcon. Software opera independentemente de esses contratos estarem assinados.

---

## 2. Arquitetura — visão alta

```
┌─────────────────────────── Home (/)  ───────────────────────────┐
│ 1. Liquidez Total (topo escuro — igual hoje)                    │
│ 2. Contas Correntes + Aplicações (igual hoje)                   │
│ 3. Evolução do Caixa (novo — 3 números + sparkline)             │
│ 4. Pra onde foi o dinheiro (4 KPIs ajustados, Saídas clicável)  │
│ 5. Compromissos em aberto + Recebíveis em atraso (novo)         │
│ 6. Receita Financeira (novo — card roxo destacado)              │
│ 7. Tendência 6m — 4 gráficos (rodapé)                           │
└─────────────────────────────────────────────────────────────────┘
     │
     ├── /dashboard/saldo              (breakdown por conta)
     ├── /dashboard/saldo-diario       (evolução diária do mês)
     ├── /dashboard/historico          (comparativo entre meses)
     ├── /dashboard/receita-financeira (rendimento por aplicação + CDI)
     ├── /dashboard/entradas           (por contratante)
     ├── /dashboard/saidas             (4 bolsos)
     │    ├── /saidas/spm, /fd, /hugo-pessoal, /investimento
     ├── /dashboard/projetado          (calendário 30/60/90d)
     ├── /dashboard/compromissos       (PP sem PIX + faturas)
     └── /dashboard/recebiveis         (aging por contratante)
```

---

## 3. Modelo de dados

### 3.1. Migrations novas

**0015_empresa_grupo_e_vinculos.sql**

Cria a tabela `empresa_grupo` para representar entidades do grupo (SPM + FD + futuras) e adiciona FKs em prestador e orcamento_linha.

```sql
CREATE TABLE empresa_grupo (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    razao_social text NOT NULL,
    cnpj text UNIQUE NOT NULL,
    regime_tributario text NOT NULL CHECK (regime_tributario IN ('LUCRO_REAL', 'LUCRO_PRESUMIDO', 'SIMPLES_NACIONAL')),
    papel text NOT NULL CHECK (papel IN ('PRINCIPAL', 'INTRAGRUPO')),
    ativa boolean NOT NULL DEFAULT true,
    criado_em timestamptz NOT NULL DEFAULT now()
);

INSERT INTO empresa_grupo (razao_social, cnpj, regime_tributario, papel) VALUES
    ('SOCIEDADE PARANAENSE DE MEDICINA LTDA', '<cnpj_spm>', 'LUCRO_REAL', 'PRINCIPAL'),
    ('FD GESTAO INTELIGENTE DE NEGOCIOS LTDA', '49.542.886/0001-94', 'SIMPLES_NACIONAL', 'INTRAGRUPO');

ALTER TABLE prestador
    ADD COLUMN pj_empregadora_id uuid REFERENCES empresa_grupo(id);
CREATE INDEX idx_prestador_pj_empregadora ON prestador(pj_empregadora_id)
    WHERE pj_empregadora_id IS NOT NULL;

ALTER TABLE orcamento_linha
    ADD COLUMN empresa_pagadora_id uuid REFERENCES empresa_grupo(id);
CREATE INDEX idx_orcamento_linha_empresa_pagadora ON orcamento_linha(empresa_pagadora_id)
    WHERE empresa_pagadora_id IS NOT NULL;
```

**0016_bolsos.sql**

Cria o enum `bolso_tipo` e adiciona coluna em `orcamento_linha`. Bolso é dimensão gerencial ortogonal à natureza — um salário variável pode ser SPM_OPERACIONAL ou FD_VIA_SPM; uma conta fixa pode ser SPM_OPERACIONAL ou HUGO_PESSOAL.

```sql
CREATE TYPE bolso_tipo AS ENUM (
    'SPM_OPERACIONAL',
    'FD_VIA_SPM',
    'HUGO_PESSOAL',
    'INVESTIMENTO_HUGO'
);

ALTER TABLE orcamento_linha
    ADD COLUMN bolso bolso_tipo NOT NULL DEFAULT 'SPM_OPERACIONAL';
CREATE INDEX idx_orcamento_linha_bolso ON orcamento_linha(bolso);

-- Backfill inicial: tudo SPM_OPERACIONAL (default). Reclassificação feita via UI por Hugo.
```

**0017_transacao_linha_split.sql**

Permite quebrar uma transação em N alocações com bolsos/naturezas/orcamento_linhas diferentes. Usado primariamente para fatura de cartão (metade SPM, metade pessoal).

```sql
CREATE TABLE transacao_linha (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    transacao_bancaria_id uuid NOT NULL REFERENCES transacao_bancaria(id) ON DELETE CASCADE,
    valor numeric(14,2) NOT NULL CHECK (valor <> 0),
    bolso bolso_tipo NOT NULL,
    orcamento_linha_id uuid REFERENCES orcamento_linha(id),
    empresa_pagadora_id uuid REFERENCES empresa_grupo(id),
    descricao text,
    criado_em timestamptz NOT NULL DEFAULT now(),
    criado_por uuid REFERENCES auth.users(id)
);

CREATE INDEX idx_transacao_linha_transacao ON transacao_linha(transacao_bancaria_id);
CREATE INDEX idx_transacao_linha_bolso ON transacao_linha(bolso);
CREATE INDEX idx_transacao_linha_orcamento ON transacao_linha(orcamento_linha_id)
    WHERE orcamento_linha_id IS NOT NULL;

-- Invariante: soma de valor das linhas filhas = valor da transação pai
-- (validado no router, não no banco — permite estados temporários durante edição)
```

**0018_saldo_diario_e_rendimento.sql**

Materializa saldo diário consolidado do caixa e adiciona coluna `rendimento_periodo` em `aplicacao_financeira_snapshot` (ou tabela equivalente — ver §3.2) para preservar precisão máxima.

```sql
CREATE TABLE saldo_caixa_diario (
    data date NOT NULL,
    empresa_grupo_id uuid NOT NULL REFERENCES empresa_grupo(id),
    saldo_contas_correntes numeric(14,2) NOT NULL DEFAULT 0,
    saldo_aplicacoes numeric(14,2) NOT NULL DEFAULT 0,
    liquidez_total numeric(14,2) GENERATED ALWAYS AS (saldo_contas_correntes + saldo_aplicacoes) STORED,
    rendimento_do_dia numeric(14,2) NOT NULL DEFAULT 0,
    entradas_do_dia numeric(14,2) NOT NULL DEFAULT 0,
    saidas_do_dia numeric(14,2) NOT NULL DEFAULT 0,
    atualizado_em timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (data, empresa_grupo_id)
);

CREATE INDEX idx_saldo_caixa_diario_data ON saldo_caixa_diario(data DESC);

-- Coluna rendimento explícito na atualização de aplicação
ALTER TABLE aplicacao_financeira
    ADD COLUMN rendimento_ultima_atualizacao numeric(14,2),
    ADD COLUMN rendimento_ultima_atualizacao_fonte text CHECK (
        rendimento_ultima_atualizacao_fonte IN ('CALCULADO', 'MANUAL', NULL)
    );
```

### 3.2. Como o saldo diário é preenchido

Opção escolhida: **derivação assíncrona em worker leve**, não trigger.

- Ao fim de qualquer operação que afete saldo (upload de extrato, atualização de aplicação manual, aprovação de rodada), o router enfileira recálculo de `saldo_caixa_diario` para as datas afetadas via `rpc fn_recalcular_saldo_diario(data_inicio, data_fim, empresa_grupo_id)`.
- A função faz `INSERT ON CONFLICT DO UPDATE` por data, calculando:
  - `saldo_contas_correntes` = soma dos saldos das contas na data (vem do parser de extrato ampliado — ver §5)
  - `saldo_aplicacoes` = valor da última `aplicacao_financeira_snapshot` na data
  - `rendimento_do_dia` = diferença entre snapshots consecutivos da mesma aplicação, menos aportes/resgates do dia
  - `entradas_do_dia`, `saidas_do_dia` = soma de `transacao_bancaria` do dia

Alternativa considerada e descartada: view materializada com refresh agendado (cron). Razão: latência de refresh inaceitável durante sessão de conciliação ativa.

### 3.3. Categoria RECEITA_FINANCEIRA

Adiciona valor ao enum `categoria_natureza_lancamento`:

```sql
-- Em 0018
ALTER TYPE categoria_natureza_lancamento ADD VALUE IF NOT EXISTS 'RECEITA_FINANCEIRA';
```

Classificador (`classificador_conciliacao.py`) ganha heurística: crédito com memo contendo `RENDIMENTO`, `JUROS`, `RESGATE APLICACAO`, `APLIC AUTOMATICA` → marca categoria RECEITA_FINANCEIRA. Rendimento manual (do campo em `aplicacao_financeira.rendimento_ultima_atualizacao`) é somado ao KPI independentemente de transação bancária.

---

## 4. Regras de conciliação

### 4.1. Regra anti-duplicidade PIX intragrupo ↔ linhas FD

Hoje: PIX SPM→FD é auto-marcado `PAGAMENTO_INTRAGRUPO` e sai do pool de sugestões (migration 0014). Isso resolve o match falso contra prestador individual.

Novo: **conciliação em lote contra linhas do orçamento com `empresa_pagadora_id = FD`**.

Ao clicar em "Conciliar" numa transação `PAGAMENTO_INTRAGRUPO`, o router:

1. Lista todas as `orcamento_linha` onde `empresa_pagadora_id = FD` e `competencia <= data_movimento` e `saldo_pendente > 0`
2. Ordena por competência ascendente (paga as mais antigas primeiro — FIFO)
3. Consome o valor do PIX sequencialmente:
   - Se valor do PIX ≥ soma das linhas pendentes: cria N conciliações (uma por linha) e o resíduo vira "adiantamento SPM→FD" em registro separado
   - Se valor do PIX < soma das linhas pendentes: consome FIFO até zerar o PIX; linhas remanescentes ficam pendentes com `saldo_parcial`
4. Cada conciliação recebe `origem = 'PAGAMENTO_INTRAGRUPO_LOTE'` e referência ao grupo de linhas para auditoria
5. Registros individuais no PP de CLTs com `prestador.pj_empregadora_id = FD` permanecem no relatório operacional mas **não entram no pool de conciliação individual** — evita duplo débito

### 4.2. Comportamento do classificador

`eh_pagamento_intragrupo(tx)` continua como está. Novo: quando `pj_empregadora_id` existe no prestador, filtrar do pool de sugestões:

```python
def filtrar_pool_sugestoes(transacoes, prestadores):
    prestadores_via_pj = {p.id for p in prestadores if p.pj_empregadora_id is not None}
    # Registros PP desses prestadores não entram no pool
    # A "sugestão" deles é sempre o PIX intragrupo consolidado
```

### 4.3. Testes críticos

Adicionar em `test_classificador.py` e novo `test_conciliacao_lote.py`:

- `test_pix_intragrupo_concilia_em_lote_fifo` — PIX R$55k consome 3 linhas FD em ordem de competência
- `test_pix_intragrupo_com_residuo_vira_adiantamento` — PIX > soma das linhas
- `test_pix_intragrupo_parcial_mantem_saldo_pendente` — PIX < soma
- `test_clt_fd_nao_entra_no_pool_individual` — prestador com `pj_empregadora_id` tem registros PP filtrados
- `test_orcamento_linha_empresa_pagadora_backfill_vazio` — linhas sem `empresa_pagadora_id` não são afetadas

---

## 5. Backend — endpoints novos e ajustes

### 5.1. Parser de extrato (ampliação)

**Hoje:** `extrato_bradesco.py` e parser Unicred capturam transações + saldo final do período.

**Novo:** capturar saldo **por dia** do período do extrato. Para Bradesco OFX, campo `LEDGERBAL` por dia está presente quando o extrato é diário — para extratos mensais, saldo diário é derivado por `saldo_inicial + soma(transacoes até dia D)`. Para Unicred PDF, já existe coluna "Saldo" por lançamento; agregar saldo de fim do dia.

Interface nova:

```python
def extrair_saldos_diarios(arquivo_extrato) -> list[dict]:
    # Retorna [{"data": date, "saldo_final": Decimal}, ...] para cada dia do período
    ...
```

Ao fim do upload do extrato, router chama `fn_recalcular_saldo_diario(data_inicio, data_fim, empresa_grupo_id)`.

### 5.2. Endpoints

Todos em `backend/api/routers/dashboard.py` (ampliação) e novos routers:

- `GET /dashboard` (refatoração):
  - Retorna os 6 blocos da home em uma única resposta
  - `saldo_atual` = `liquidez_total` do snapshot mais recente (fix do bug)
  - Remove `saldo_inicial` hardcoded = 0, substitui por `entradas_do_mes`
  - Remove `previsto_a_pagar` = 0, substitui por `caixa_projetado_30d`
  - Adiciona `evolucao_caixa`, `compromissos_em_aberto`, `recebiveis_em_atraso`, `receita_financeira`

- `GET /dashboard/saldo-diario?mes=YYYY-MM`:
  - Retorna tabela dia-a-dia: abertura, entradas, saídas, rendimento, fechamento
  - Série temporal agrupada por conta e consolidada

- `GET /dashboard/historico?meses=N` (default 6):
  - Abertura, fechamento, variação, rendimento por mês
  - Base para os gráficos de tendência do rodapé da home

- `GET /dashboard/receita-financeira?mes=YYYY-MM`:
  - Rendimento do mês (soma manual + classificado)
  - Acumulado ano
  - Rentabilidade % (rendimento / saldo médio do mês)
  - Comparação vs CDI (taxa CDI lida de constante config, não é API externa — simplificação consciente)

- `GET /dashboard/compromissos`:
  - `sum(registro_pp WHERE status_saldo=ELEGIVEL)` agrupado por competência
  - Menos `sum(transacao_bancaria WHERE conciliada_com_pp)`
  - Agrega também `orcamento_linha WHERE data_previsao <= now() + 30 days AND saldo_pendente > 0` (faturas a vencer)

- `GET /dashboard/recebiveis`:
  - Aging por contratante: linhas de entrada esperadas do orçamento com `data_previsao < today` e sem transação conciliada
  - Agrupamento: 0-30d, 30-60d, 60-90d, 90d+ de atraso
  - Requer modelo de orçamento de entrada — **pré-requisito**: `orcamento_linha` já aceita entradas (sinal de valor), só falta garantir preenchimento por contratante

- `GET /dashboard/saidas?bolso=BOLSO`:
  - Linhas de orçamento + transações realizadas, filtradas por bolso
  - Drill-down por natureza, por prestador, até transação individual

- `POST /aplicacoes/{id}/atualizar` (endpoint existente — ampliação):
  - Body ganha campo `rendimento_manual: Decimal | None`
  - Se None, sistema calcula `novo_saldo - saldo_anterior - aporte + resgate`
  - Campo `rendimento_ultima_atualizacao_fonte` gravado como 'CALCULADO' ou 'MANUAL' conforme origem

### 5.3. Fixes de bugs identificados na auditoria (Agent 4)

Os que são resolvidos neste spec:

- ✅ `saldo_inicial = 0` hardcoded (`dashboard.py:176-177`) — removido, substituído por `entradas_do_mes` que calcula da tabela
- ✅ `saldo_atual ≠ liquidez_total` — passa a usar a Liquidez Total

Os que **não** são resolvidos aqui (reforço do que fica fora):

- ⚠ UUID hardcoded `CONTA_BRADESCO_REMESSAS_ID` (`rodadas.py:103`) — backlog separado
- ⚠ Rollback parcial com `pass` silencioso (`rodadas.py:293-317`) — backlog
- ⚠ RPC `fn_aprovar_rodada()` atômica — backlog (risco de corrupção)
- ⚠ `orcamento.replicar` com `data_previsao` stale — backlog

---

## 6. Frontend

### 6.1. Componentes novos

- `<EvolucaoCaixaCard />` — 3 números + sparkline SVG inline 22 pontos, altura 50px
- `<ReceitaFinanceiraCard />` — fundo roxo com gradiente, 3 números (rendimento mês · acumulado ano · rentab. %)
- `<CompromissosCard />` e `<RecebiveisCard />` — estilo semelhante, cores laranja e vermelha
- `<Sparkline data={Array<number>} />` — componente genérico reutilizável
- `<GraficoTendencia tipo="area|bar|stacked-bar|line-dual" dados={...} />` — fundação dos 4 gráficos do rodapé com hover tooltip
- `<BolsoSelect />` — select usado em `/dashboard/saidas` e na edição de linha de orçamento

### 6.2. Subpáginas

Listadas na árvore de §2. Cada uma é uma página Next.js em `frontend/app/dashboard/<slug>/page.tsx`. Padrão: header com breadcrumb "← Voltar · <contexto>" · filtros (mês, conta, bolso) · conteúdo principal.

### 6.3. Edição de linha de orçamento

Ajuste na UI existente:

- Modal de edição de `orcamento_linha` ganha dois selects:
  - **Bolso** (4 opções, default SPM_OPERACIONAL)
  - **Empresa pagadora** (SPM · FD · nenhuma — default nenhuma, significa pago direto pela conta da própria empresa dona do orçamento)
- Linhas com `empresa_pagadora_id = FD` recebem badge visual "[FD]" na lista de linhas

### 6.4. Split de transação

Tela nova `/transacoes/{id}/split`:

- Campos: valor da transação original (readonly), lista editável de linhas (valor, bolso, orcamento_linha opcional, descrição)
- Validação client-side: soma das linhas = valor da transação (±R$ 0,01)
- Atalhos para acelerar o preenchimento: "Dividir 50/50 SPM/Hugo pessoal", "Copiar divisão do mês anterior" (última transação do mesmo titular que teve split), campo "% SPM" com cálculo automático do restante
- Persistência do padrão: ao salvar, sistema memoriza a divisão por titular (ex: "fatura Unicred CC 9999 → 58% SPM / 42% pessoal") para pré-preencher em próximas faturas do mesmo cartão

**Sem integração FaturaAI no MVP.** Projetos paralelos, sem API runtime entre eles hoje. Split é 100% feito na UI SPM.

**Evolução planejada (não bloqueante):** API de export do FaturaAI → SPM. O FaturaAI já faz a classificação SPM/pessoal/outros da fatura de cartão; quando a API existir, SPM consome via endpoint novo `POST /transacoes/{id}/split/import` que recebe o payload e cria as linhas `transacao_linha` pré-preenchidas — usuário só revisa e confirma. Não exige mudança no modelo de dados do Track B (tabela `transacao_linha` já suporta). Fica como rota de aceleração, a UI manual permanece.

### 6.5. Atualização de aplicação com rendimento

Modal existente em `/dashboard/saldo` ganha:

- Campo "Aporte no período" (default 0)
- Campo "Resgate no período" (default 0)
- Exibição calculada: `Rendimento = Novo saldo − Saldo anterior − Aporte + Resgate`
- Campo editável "Ajustar rendimento (opcional)" pré-preenchido com o calculado
- Se Hugo altera, grava `fonte = 'MANUAL'`; se mantém, grava `fonte = 'CALCULADO'`

---

## 7. Testes de aceitação (crítica)

### 7.1. Backend

- `test_dashboard_saldo_atual_igual_liquidez` — KPI "saldo atual" do /dashboard bate com `liquidez_total` de `/saldos/dashboard`
- `test_dashboard_entradas_mes_soma_creditos` — soma `transacao_bancaria` com valor > 0 na competência
- `test_dashboard_caixa_projetado_30d` — `liquidez_total - compromissos_30d + recebiveis_atrasados`
- `test_bolso_soma_por_natureza` — agrupamento correto em `/dashboard/saidas`
- `test_split_soma_igual_transacao` — soma de `transacao_linha` = valor da `transacao_bancaria` pai
- `test_rendimento_calculado_vs_manual` — `fonte` reflete origem
- `test_saldo_diario_invariante` — abertura + entradas − saídas + rendimento = fechamento, para cada dia e mês

### 7.2. Frontend (e2e)

- `test_home_sem_grafico_donut_na_home` — página inicial não renderiza o componente donut
- `test_clicar_saidas_abre_4_bolsos` — `/dashboard/saidas` mostra os 4 cards
- `test_sparkline_renderiza_22_pontos` — mês com 22 dias úteis
- `test_modal_aplicacao_pre_calcula_rendimento` — modifica saldo, campo rendimento atualiza

---

## 8. Plano de rollout (alto nível — detalhado no plano de implementação)

Fases com valor independente (cada uma pode ir para produção sozinha):

**Fase A — Modelo de dados + backfill (sem impacto visível)**
- Migrations 0015, 0016, 0017, 0018
- Backfill: tudo SPM_OPERACIONAL, empresa_pagadora=null em todas as linhas
- CLTs FD têm `pj_empregadora_id` preenchido via script (lista: Thais, Vinicius, CLTs Unai)

**Fase B — Fixes de bug no Dashboard atual**
- Remove saldo_inicial=0 hardcoded, passa a usar entradas_do_mes
- Corrige saldo_atual usando Liquidez Total
- Visível imediatamente, zero risco

**Fase C — Home refinada (ocultando gráficos donut/barras)**
- Layout novo com os 6 blocos
- Sparkline + card Evolução do Caixa
- Cards Compromissos/Recebíveis/Receita Financeira
- 4 gráficos de tendência no rodapé
- Subpáginas de drill-down (iteração)

**Fase D — Motor de bolsos e split**
- UI de edição de linha com Bolso + Empresa Pagadora
- Tela de split de transação
- `/dashboard/saidas` com filtro por bolso

**Fase E — Regra anti-duplicidade PIX→FD**
- Conciliação em lote contra linhas com empresa_pagadora=FD
- Filtro de CLTs FD do pool individual

**Fase F — Rendimento explícito e saldo diário**
- Parser amplia extração de saldo por dia
- `fn_recalcular_saldo_diario` disparada nos eventos
- Modal de aplicação com rendimento editável
- Subpáginas `/saldo-diario` e `/historico`

---

## 9. Dependências e riscos

**Dependências externas:** nenhuma. Tudo dentro do repo + Supabase.

**Riscos:**

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Parser Bradesco não consegue derivar saldo diário para alguns extratos | Média | Fallback: aceitar nulo e pedir upload manual de saldo naquele dia |
| Backfill de `empresa_pagadora_id` errado (linhas FD marcadas como não-FD) | Alta se automatizado | Script separado, Hugo revisa lista antes de aplicar |
| Cálculo de CDI fixo no config fica desatualizado | Baixa | Campo de config acessível em Cadastros, atualizado manualmente |
| UI de split vira tela complexa que ninguém usa em volume | Média | Atalhos (50/50, "copiar mês anterior") + memorização de padrão por titular → 2º mês de uso da mesma fatura vira 1 clique |
| Conciliação em lote muda comportamento que Hugo espera para algum cenário específico | Alta | Cada aprovação de rodada já é imutável (snapshot SHA256) — retrocompatibilidade via flag `usa_conciliacao_lote` ligada após primeira aprovação bem-sucedida |

---

## 10. Convenções e escopo

**O sistema faz:**
- Separa bolsos financeiros via dimensão gerencial
- Split de transações
- Vincula prestador a PJ empregadora (evita duplicidade CLT FD ↔ PP)
- Dashboard consolidador sobre o caixa SPM
- Rendimento explícito em aplicações

**O sistema NÃO faz:**
- Emitir NFE
- Escriturar livros contábeis por CNPJ
- Formalizar contratos inter-company (SPM↔FD) ou mútuo com sócio
- Gerar apurações tributárias

Quando tema jurídico-contábil surgir durante implementação, apontar para `~/second-brain/dominios/spm/recomendacoes-juridico-contabeis.md` e manter foco no software.

---

## 11. Glossário

- **Bolso**: dimensão gerencial de 4 valores (SPM_OPERACIONAL, FD_VIA_SPM, HUGO_PESSOAL, INVESTIMENTO_HUGO). Ortogonal à natureza.
- **PJ empregadora**: empresa do grupo que formalmente emprega um prestador. Quando populada em `prestador.pj_empregadora_id`, o PIX de pagamento vai para a PJ, não para o prestador direto.
- **Empresa pagadora**: empresa do grupo responsável por cobrir uma linha do orçamento. Quando populada, linha é conciliada via PIX consolidado em lote, não individual.
- **PAGAMENTO_INTRAGRUPO**: categoria já existente (migration 0014). Saída real do caixa SPM para FD. Distinta de TRANSFERENCIA_INTERNA (que é SPM Bradesco ↔ SPM Unicred).
- **Saldo diário consolidado**: linha em `saldo_caixa_diario` para uma data × empresa_grupo. Abertura + entradas − saídas + rendimento = fechamento.
- **Rendimento manual vs calculado**: rendimento pode vir calculado (novo saldo − anterior − aporte + resgate) ou sobrescrito por Hugo com o valor exato do extrato da aplicação. Ambos preservados para auditoria.

---

**Status deste documento:** aprovado em brainstorm visual (2026-04-22). Aguarda revisão escrita de Hugo antes de gerar plano de implementação via skill `superpowers:writing-plans`.
