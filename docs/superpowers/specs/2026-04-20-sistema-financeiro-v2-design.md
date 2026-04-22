# SPM Sistema Financeiro v2 — Design Spec (Fase 1)

- **Autor:** Hugo Damasceno (com Claude Code)
- **Data:** 2026-04-20
- **Status:** aprovado em brainstorm, pendente implementação
- **Sessão:** brainstorm de 2026-04-20, branch `main` do repo `spm-sistemafinanceiro`
- **Mockups navegáveis:** `.superpowers/brainstorm/3056-1776662200/content/` (conciliacao-v1.html, dashboard-contratos.html, orcamento-v2.html)

---

## 1. Contexto e problema

O sistema hoje (commit `a423888` e derivados) faz conciliação de **Pagamentos do Pega Plantão × extrato Bradesco REMESSAS** com motor que chega a 93,04% na rodada de referência. Entrega-se uma rodada por vez: Hugo sobe extrato + PP, sistema bate, mostra resultado.

O que está **fora** do sistema atual — e é feito manualmente, com XLSX + conferência linha a linha — é todo o resto da operação financeira mensal:

- Despesas fixas (aluguel, energia, softwares, contabilidade, planos de saúde) pagas pela Unicred
- Tributos (DARF, ISS, FGTS, PIS, COFINS, IRPJ, CSLL, parcelamentos)
- Salários e comissões (CLTs + coordenadora + equipe variável)
- Pagamentos variáveis eventuais (passagens, reembolsos, material, cartões de crédito)
- Adiantamentos a prestadores e sua posterior compensação no PP
- Despesas da empresa FD (estrutura auxiliar do grupo, cujo orçamento hoje vive dentro do XLSX da SPM)

Hugo gasta horas por mês cruzando extrato × XLSX × PP para saber "pra onde foi o dinheiro" e "o que ainda falta pagar". **Este é o norte desta fase: substituir essa conferência manual por conciliação automática, com regras aprendíveis que melhoram a cada mês.**

## 2. Escopo

### 2.1 Dentro da Fase 1

1. Visão consolidada por **contrato × competência** (DRE embrionário por contrato: receita prev, despesa prev, despesa real, margem, lista de prestadores com data e valor pagos).
2. Módulo de **despesas administrativas** (fixas + extras) com upload via XLSX modelo e cadastro/edição na UI.
3. Módulo de **tributos** com o mesmo fluxo das administrativas.
4. **Adiantamentos** como linha de saída de caixa, com **compensação manual** contra PP futuro (auto fica para Fase 2). Inclui reconhecimento de receita financeira na compensação.
5. **Orçamento mensal** com upload XLSX inicial, replicação mês a mês e edição pontual. Granularidade por subcategoria.
6. **Conciliação automática** extrato Bradesco + Unicred ↔ orçamento, com sugestão em 3 camadas (regra salva → similaridade → valor).
7. **Dashboard** "pra onde foi o dinheiro" com KPIs, donut por natureza, barras Previsto × Realizado, alertas.
8. Suporte às empresas **SPM** e **FD** no mesmo schema (dimensão `empresa`, extensível para AHAPS/MedSupport depois).

### 2.2 Fora da Fase 1

- Receita realizada (recebimentos de contratantes) → Fase 2
- Compensação **automática** de adiantamento (esta fase é manual) → Fase 2
- Caixa inicial/final projetados → Fase 2
- Orçamento P×R histórico multi-mês (séries temporais) → Fase 2
- Outras empresas do grupo (AHAPS, MedSupport) → Fase 3
- Multi-usuário com perfis completos (esta fase é só Hugo; Victor empacota depois) → Fase 3

## 3. Arquitetura macro

```
┌── INPUTS ─────────────────────────────────────────────────────┐
│ PP XLSX │ Bradesco OFX │ Unicred PDF │ Orçamento XLSX (anual) │
└────┬────────────┬────────────┬────────────────┬──────────────┘
     ▼            ▼            ▼                ▼
┌───────────────────────────────────────────────────────────────┐
│                MOTOR ÚNICO DE CONCILIAÇÃO                     │
│  • PP ↔ Bradesco REMESSAS (motor atual — 93%)                 │
│  • Orçamento ↔ Unicred + Bradesco AVISTA/TRIBUTOS             │
│  • Classificação em cascata: regra → similaridade → valor     │
└─────────────────────────┬─────────────────────────────────────┘
                          ▼
┌───────────────────────────────────────────────────────────────┐
│                   LEITURAS (telas)                            │
│  Dashboard · Conciliação · Contratos × Competência ·          │
│  Orçamento · Adiantamentos · Extratos · Cadastros             │
└───────────────────────────────────────────────────────────────┘
```

### 3.1 Princípio arquitetural único

**Orçamento é a lista-mestre. Extrato é a evidência de pagamento. Conciliação é o que liga os dois.**

Toda linha de saída de caixa existe em um dos três estados:

1. **Prevista** — existe no orçamento, não há PIX reconciliado ainda
2. **Realizada** — existe PIX no extrato + `conciliacao_orcamento` ligando ao orçamento
3. **Não prevista** — PIX no extrato sem linha de orçamento correspondente (alerta)

A dor de Hugo mora no estado 3. Mitigação: sugestão automática por regra salva + similaridade.

## 4. Modelo de dados

### 4.1 Tabelas novas (7)

| Tabela | Papel |
|---|---|
| `empresa` | SPM, FD (e futuramente AHAPS, MedSupport). Dimensão cross-cutting |
| `projeto` | Centro de custo ("MG-UNAI", "AD-DIRETORIA DE LICITAÇÕES-SPM") |
| `categoria_despesa` | Natureza ("Energia Elétrica", "Aluguel", "Software") |
| `orcamento` | Cabeçalho por `(empresa, competencia)`, status, criador |
| `orcamento_linha` | Uma linha = uma linha do XLSX. Chave de conciliação |
| `conciliacao_orcamento` | Associativa N:N (`transacao_id`, `orcamento_linha_id`, `valor_aplicado`) |
| `regra_classificacao` | Aprendizado: `titular_pix_padrao → orcamento_linha_sugerida` |

### 4.2 Extensões em tabelas existentes

| Tabela | Coluna nova |
|---|---|
| `transacao_bancaria` | `origem_banco ∈ {BRADESCO, UNICRED}` |
| `transacao_bancaria` | `natureza_lancamento` (enum ampliado: PIX, LIQ_TIT, CONVENIO, INTEGRALIZACAO, ARRECADACAO, TARIFA, ESTORNO) |
| `adiantamento` | `status ∈ {ABERTO, COMPENSADO_PARCIAL, COMPENSADO_TOTAL, BAIXADO_MANUAL}` |
| `adiantamento` | `compensado_em_registro_pp_id uuid FK registro_pp NULL` |
| `registro_pp` | `orcamento_linha_id uuid FK orcamento_linha NULL` — habilita pivot direto contra orçamento na seção PROFISSIONAIS |

### 4.3 Enums novos

```sql
CREATE TYPE natureza_orcamento AS ENUM (
  'DESPESA_FIXA',
  'TRIBUTO',
  'SALARIO_VARIAVEL',
  'COMISSAO',
  'VALOR_VARIAVEL',
  'DESPESA_PROFISSIONAIS'
);

CREATE TYPE status_orcamento_linha AS ENUM (
  'PREVISTO',
  'PAGO_PARCIAL',
  'PAGO_TOTAL',
  'PAGO_A_MAIOR',
  'CANCELADO'
);
-- Calculado dinamicamente via view:
--   SUM(conciliacao_orcamento.valor_aplicado) vs orcamento_linha.valor_previsto

CREATE TYPE adiantamento_status AS ENUM (
  'ABERTO', 'COMPENSADO_PARCIAL', 'COMPENSADO_TOTAL', 'BAIXADO_MANUAL'
);
```

O enum existente `categoria_conciliacao` não é estendido. Despesas administrativas, tributos e variáveis seguem pelo caminho `conciliacao_orcamento` (tabela N:N nova), enquanto o motor PP continua usando `transacao_bancaria.registro_pp_id` + `categoria_conciliacao` como hoje.

### 4.4 Schema SQL resumido das tabelas novas

```sql
-- Empresa (dimensão)
CREATE TABLE empresa (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo text NOT NULL UNIQUE,           -- 'SPM', 'FD', 'AHAPS', 'MEDSUPPORT'
  razao_social text NOT NULL,
  cnpj text,
  ativa boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Projeto (centro de custo)
CREATE TABLE projeto (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo text NOT NULL UNIQUE,           -- 'AD-DIRETORIA GERAL-SPM', 'MG-UNAI'
  descricao text,
  empresa_id uuid NOT NULL REFERENCES empresa(id),
  ativo boolean NOT NULL DEFAULT true
);

-- Categoria (natureza da despesa)
CREATE TABLE categoria_despesa (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome text NOT NULL UNIQUE,
  descricao text
);

-- Orçamento (cabeçalho mensal)
CREATE TABLE orcamento (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id uuid NOT NULL REFERENCES empresa(id),
  competencia text NOT NULL CHECK (competencia ~ '^\d{4}-\d{2}$'),
  status text NOT NULL DEFAULT 'RASCUNHO'
    CHECK (status IN ('RASCUNHO','VALIDADO','FECHADO')),
  criado_por uuid REFERENCES usuario(id),
  criado_em timestamptz NOT NULL DEFAULT now(),
  validado_em timestamptz,
  fechado_em timestamptz,
  UNIQUE (empresa_id, competencia)
);

-- Linha do orçamento
CREATE TABLE orcamento_linha (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  orcamento_id uuid NOT NULL REFERENCES orcamento(id) ON DELETE CASCADE,
  natureza natureza_orcamento NOT NULL,
  categoria_id uuid REFERENCES categoria_despesa(id),
  projeto_id uuid REFERENCES projeto(id),
  titular_cpf_cnpj text,
  titular_razao_social text NOT NULL,
  contrato_id uuid REFERENCES contrato(id),        -- só para natureza PROFISSIONAIS
  valor_previsto numeric(14,2) NOT NULL,
  data_previsao date,
  observacao text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Conciliação extrato ↔ orçamento (N:N)
CREATE TABLE conciliacao_orcamento (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  transacao_id uuid NOT NULL REFERENCES transacao_bancaria(id),
  orcamento_linha_id uuid NOT NULL REFERENCES orcamento_linha(id),
  valor_aplicado numeric(14,2) NOT NULL CHECK (valor_aplicado > 0),
  confianca numeric(3,2),                           -- 0.30 ~ 1.00
  origem text NOT NULL CHECK (origem IN ('REGRA','SIMILARIDADE','VALOR','MANUAL')),
  aprovada_por uuid REFERENCES usuario(id),
  aprovada_em timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_conc_tx ON conciliacao_orcamento(transacao_id);
CREATE INDEX idx_conc_linha ON conciliacao_orcamento(orcamento_linha_id);

-- Regra aprendível
CREATE TABLE regra_classificacao (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  titular_pix_padrao text NOT NULL,                 -- normalizado (upper, sem acento, trim)
  orcamento_linha_id uuid REFERENCES orcamento_linha(id),
  categoria_id uuid REFERENCES categoria_despesa(id),
  projeto_id uuid REFERENCES projeto(id),
  empresa_id uuid REFERENCES empresa(id),
  confianca_base numeric(3,2) NOT NULL DEFAULT 0.95,
  uso_count integer NOT NULL DEFAULT 0,
  ativa boolean NOT NULL DEFAULT true,
  criada_por uuid REFERENCES usuario(id),
  criada_em timestamptz NOT NULL DEFAULT now(),
  ultima_utilizacao timestamptz,
  UNIQUE (titular_pix_padrao, ativa) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX idx_regra_titular ON regra_classificacao (lower(titular_pix_padrao));
```

Todas as tabelas ganham RLS habilitada com policies consistentes com o padrão atual (`auth.uid() IS NOT NULL` para SELECT/INSERT/UPDATE; `fn_is_ceo()` para DELETE). Trigger de `log_auditoria` aplicado via `fn_log_auditoria` já existente.

### 4.5 Decisões-chave de modelagem

1. **Uma tabela `orcamento_linha` em vez de 6 por seção.** Discriminador é `natureza`. Uma API, um dashboard, validações por aplicação.
2. **Conciliação extrato↔orçamento em tabela N:N.** Permite fracionamento (1 linha paga em 2 PIX), agrupamento (1 fatura de cartão paga várias linhas) e desfazer match sem perder dados.
3. **`registro_pp_id` em `transacao_bancaria` continua existindo.** Motor PP atual (93%) não é reescrito. Dois caminhos de conciliação coexistem: PP usa FK direta; resto usa `conciliacao_orcamento`. Unificação fica para Fase 3.
4. **`empresa_id` em `orcamento_linha`, não em `transacao_bancaria`.** Um PIX da conta SPM pode pagar linha FD. Associação empresa↔fato mora na responsabilidade (linha), não no instrumento (transação).
5. **`regra_classificacao` cresce com o uso.** Toda aprovação manual gera ou atualiza uma regra automaticamente. É o mecanismo central de eliminação da conferência manual.

## 5. Fluxos principais

### 5.1 F1 — Ingestão de orçamento

**Upload inicial (uma vez por empresa):**
1. Usuário faz upload do XLSX de orçamento.
2. Parser detecta 6 subcabeçalhos: `DESPESAS FIXAS`, `TRIBUTOS`, `DESPESAS VARIÁVEIS`, `COMISSÕES`, `Pagamentos de Valores Variáveis`, `DESPESAS DE PROFISSIONAIS`.
3. Para cada linha válida (CNPJ ou Razão Social presente), extrai `CNPJ/CPF`, `Razão Social`, `Categoria`, `Projeto`, `Valor`, `Data`, `Observação`.
4. Deriva `empresa_id` pelo sufixo do projeto (`-FD` → FD; padrão → SPM).
5. Cria/encontra `projeto`, `categoria_despesa` (tabelas-catálogo preenchidas na primeira passada).
6. Cria `orcamento_linha` com `natureza` derivada da seção.
7. Para seção `DESPESAS DE PROFISSIONAIS`: tenta casar o campo Projeto com `contrato.local_pp` por similaridade fuzzy (limiar 0.80) → associa `contrato_id` ou marca para revisão manual.
8. Tela de validação mostra: o que foi parseado, linhas ambíguas, linhas não reconhecidas. Hugo revisa e clica "Salvar orçamento".

**Replicação mensal:**
1. Botão "Replicar para 05/2026" no card do mês atual.
2. Sistema clona todas as `orcamento_linha` da competência anterior (sem `conciliacao_orcamento`).
3. Usuário edita linhas que mudaram (valor, data, observação) e clica "Validar".
4. Status do mês passa de `RASCUNHO` → `VALIDADO`.

### 5.2 F2 — Ingestão de extratos

**Bradesco OFX** (REMESSAS, AVISTA, TRIBUTOS): parser existente estendido para rotear transações por `conta_id` (determinado via `BANKID` + `ACCTID`). Marca `origem_banco='BRADESCO'`.

**Unicred PDF**:
- Parser novo usando `pdfplumber`
- Regex de linha: `(\d{2}/\d{2}/\d{4})\s+(\S+)\s+(.+?)\s+(-?[\d\.]+,\d{2})\s+([\d\.]+,\d{2})$`
- Lookahead para quebras de linha onde valor aparece na linha seguinte
- Classificador de `natureza_lancamento` baseado no texto do campo HISTÓRICO:
  - `CRED PIX ... RECEBIMENTO PIX(...)` → `PIX_CREDITO`
  - `DEB PIX ... DEBITO TRANSF PIX(...)` → `PIX_DEBITO`
  - `LIQ TIT - IB(...)` → `LIQUIDACAO_TITULO`
  - `ARREC CONVENIO(...)` → `CONVENIO`
  - `INTEGR PARC CAPIT` → `INTEGRALIZACAO_CAPITAL`
  - `TRANSF TEF PIX(...)` → `PIX_TEF`
  - `CRD DEVPIX` / `ESTORNO PIX PAGO` → `ESTORNO`
  - `PJ CONTA PJ 1` → `TARIFA_CONTA`
- Extrai `titular_pix` do conteúdo entre parênteses no HISTÓRICO, normalizado
- Marca `origem_banco='UNICRED'`, `status_conciliacao='NAO_CLASSIFICADO'` (exceto estornos e transferências internas detectáveis)

### 5.3 F3 — Processamento PP

Motor atual mantido (93,04% na rodada 22f82135). Ajustes mínimos:
- `registro_pp` ganha FK opcional `orcamento_linha_id` para natureza `DESPESA_PROFISSIONAIS` da competência correspondente (permite pivot direto)
- Status `MATCH_AUTOMATICO`, `FRACIONADO`, `CONCILIADO_POR_CATEGORIA` mantidos

### 5.4 F4 — Conciliação extrato ↔ orçamento (tela central)

Tela de duas colunas: **Transações não conciliadas** (esquerda) × **Orçamento pendente** (direita).

Sugestão automática em 3 camadas:

```
Camada 1 — REGRA SALVA (confiança ≥0.95):
  SELECT * FROM regra_classificacao
  WHERE lower(titular_pix_padrao) = lower(normalize(transacao.titular_pix))
    AND ativa = true
  → sugere orcamento_linha memorizada; badge verde

Camada 2 — SIMILARIDADE + VALOR (confiança 0.70-0.90):
  CROSS JOIN transacao × orcamento_linha
  WHERE mesmo orcamento (empresa, competência)
    AND similarity(transacao.titular_pix, orcamento_linha.razao_social) > 0.75
    AND abs(transacao.valor - orcamento_linha.saldo_pendente) / valor < 0.02
  → badge amarelo

Camada 3 — VALOR ÚNICO (confiança 0.30-0.60):
  Para linhas sem similaridade boa, busca orcamento_linha com
  valor_previsto == transacao.valor e não paga ainda.
  Se só existe 1, sugere.
  → badge cinza, requer revisão manual
```

**Comportamento ao aprovar:**
- Cria registro em `conciliacao_orcamento`
- Se match veio de camada 2/3 (não de regra salva), cria/atualiza `regra_classificacao`:
  - `titular_pix_padrao` = normalização do titular
  - `orcamento_linha_id` = a linha aprovada
  - `empresa_id`, `categoria_id` = derivados
  - `confianca_base` = 0.95
  - Na próxima vez, mesmo titular → camada 1 automática

**Fracionamento:** usuário seleciona múltiplas transações + uma linha (ou o inverso) → botão "Casar fracionado" cria vários registros em `conciliacao_orcamento` somando ao total.

**Botão "Confirmar TODOS os sugeridos":** aplica todos os matches de camada 1 em bloco. Elimina tipicamente 70-90% do trabalho de conciliação mensal.

### 5.5 F5 — Leituras

**Visão Contrato × Competência:**
- Agregação `(contrato_id, mes_competencia)` atravessando rodadas
- Métricas: total devido (soma `registro_pp.saldo_pp`), total pago (soma transações via `registro_pp_id`), % pago, prestadores linha a linha
- Integração com `orcamento_linha` de natureza `DESPESA_PROFISSIONAIS`: receita prevista + margem projetada

**Dashboard "pra onde foi o dinheiro":**
- Header: saldos agregados das contas (Bradesco + Unicred) início e fim de mês
- Donut por natureza (variáveis / fixas / tributos / comissões / adiantamentos)
- Barras Previsto × Realizado por categoria
- Alertas: transações não conciliadas há > 5 dias, linhas vencidas sem pagamento, pago a maior, estornos pendentes

### 5.6 F6 — Compensação manual de adiantamento

Ao processar PP, motor identifica prestadores com `adiantamento.status='ABERTO'`. Alerta visual na tela de conciliação da rodada. Usuário:
1. Vê alerta com valor do adiantamento e desconto calculado
2. Decide valor ajustado (PP − adiantamento) e faz o PIX
3. Clica "Marcar compensação" — sistema atualiza `adiantamento.status='COMPENSADO_TOTAL'` + `compensado_em_registro_pp_id`
4. Receita financeira (`valor_bruto − valor_liquido`) é lançada automaticamente

Automação da sugestão de valor ajustado fica para Fase 2.

## 6. UI

7 telas principais. Filtro global de **empresa** (SPM/FD/agregadas) e **competência** no topbar.

| Tela | Rota | Papel |
|---|---|---|
| Dashboard | `/` | Home: KPIs, donut, barras P×R, alertas |
| Conciliação | `/conciliacao` | **Tela crítica.** 2 colunas, sugestão cascata, confirmar em lote |
| Contratos × Competência | `/contratos` | Lista com receita/despesa/margem, drilldown |
| Rodadas PP | `/rodadas` | Existente, pequenas adições |
| Orçamento | `/orcamento` | Strip meses + 6 abas por seção + tabela editável |
| Adiantamentos | `/adiantamentos` | Lista com filtros, modal "Marcar compensação" |
| Extratos | `/extratos` | Upload Unicred PDF / Bradesco OFX + listagem |
| Cadastros | `/cadastros` | CRUD projetos, categorias, contas, regras |

### 6.1 Convenção de colunas obrigatória

Em qualquer tabela que tenha colunas **Data** e **Status**, a ordem é sempre **Data → Status** (Status depois). Regra definida por Hugo durante brainstorm e aplicada a Orçamento, Conciliação, Contratos, Rodadas, Extratos.

### 6.2 Stack

- Frontend: Next.js 16 + TypeScript + Tailwind + shadcn/ui (tema neutral)
- Desktop-first. Mobile fora do escopo da Fase 1.
- Tabelas compactas (`Table` do shadcn).

Mockups de alta fidelidade em `.superpowers/brainstorm/3056-1776662200/content/`:
- `conciliacao-v1.html`
- `dashboard-contratos.html`
- `orcamento-v2.html`

## 7. Parsers e motor de classificação

Detalhes nas seções 5.2 (parsers) e 5.4 (motor). Pontos adicionais de implementação:

### 7.1 Heurísticas especiais

- **Estorno:** par `(titular, valor, estorno)` dentro de 7 dias marca ambas as transações como `ESTORNO_COMPENSADO` — não entram em saídas de caixa
- **Integralização de capital Unicred:** natureza fixa `CAPITALIZACAO_COOPERATIVA`, sempre fora de despesa
- **Transferência interna:** titular = razão social da própria empresa e conta destino é outra conta SPM → `TRANSFERENCIA_INTERNA`
- **Pagamento ao sócio** (titular = "HUGO FERNANDES DAMASCENO"): **nunca** gera regra automática. Toda classificação é manual (pró-labore, reembolso, retirada de lucro, ressarcimento são naturezas distintas que mudam conforme a intenção)

### 7.2 Testes de parser

| Alvo | Expectativa |
|---|---|
| Unicred PDF (arquivo de amostra `Comp-20042026014849.pdf`) | ≥95% das linhas extraídas corretamente; linhas com falha geram log estruturado |
| Orçamento XLSX (`SPM - Orcamento - 04.2026.xlsx`) | 100% das 6 seções detectadas; todas as linhas válidas parseadas |
| Bradesco OFX (todos) | Mantém 100% atual |
| Motor PP (rodada 22f82135) | Mantém 93,04% — nenhuma regressão |

## 8. Plano de entrega

Seis marcos incrementais. Cada marco tem entregáveis testáveis.

### M1 — Modelagem + Migrations (1-2 dias)
- Migrations 0006-0008 (tabelas novas + extensões)
- Seeds: `empresa` (SPM, FD), `categoria_despesa` + `projeto` derivados do XLSX real
- Validação: CRUD via Supabase, log de auditoria funcionando

### M2 — Parsers (3-5 dias)
- Parser Orçamento XLSX
- Parser Unicred PDF
- Extensão Bradesco (roteamento por `conta_id`)
- Testes unitários contra arquivos reais de Hugo

### M3 — Motor de Classificação + API (3-4 dias)
- 3 camadas em cascata
- Endpoints: `POST /orcamentos/upload`, `POST /extratos/unicred/upload`, `POST /conciliacoes`, `GET /conciliacoes/sugestoes`, CRUD `regra_classificacao`, CRUD `adiantamento` com lifecycle
- Testes: cada camada + cascata + fracionamento + estorno

### M4 — UI Telas Principais (5-7 dias)
- 7 telas com filtros globais no topbar
- Regra **Data → Status** aplicada consistentemente
- Tela de conciliação com botão "Confirmar TODOS sugeridos"

### M5 — Integração + Dados Reais (2-3 dias)
- Importa XLSX orçamento 04/26 real
- Importa PDF Unicred período 22/03-20/04
- Primeira conciliação real — ajuste de parser se necessário
- Valida alertas, pago a maior, estornos

### M6 — Validação em Produção (1-2 dias)
- Deploy Render (backend) + Vercel (frontend)
- Hugo opera 1 ciclo mensal completo
- Feedback vira ajustes

**Esforço total: 15-23 dias úteis (3-5 semanas calendáricas).**

Paralelização possível a partir do M3 se Victor/TI entrarem para UI enquanto backend é refinado.

## 9. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Unicred muda layout do PDF → parser quebra | Validar hash do layout no upload; alerta visual se diverge; fallback para cadastro manual da linha que falhou |
| Orçamento com linhas ambíguas na seção PROFISSIONAIS | Tela de revisão manual antes de salvar; linhas sem match `contrato.local_pp` ficam destacadas |
| Regra aprendível classifica errado após mudança de política (ex: troca fornecedor) | Regras são editáveis e desativáveis; UI mostra contador de uso para Hugo avaliar |
| Motor PP atual (93%) regride com extensões | Toda mudança em `conciliacao_spm.py` tem que passar no teste de regressão da rodada 22f82135 |
| Dados sensíveis em tabelas (razão social PIX do sócio, fornecedores do grupo familiar) | RLS já ativa; apenas Hugo acessa na Fase 1; quando multi-usuário entrar (Fase 3), adicionar policies por perfil |

## 10. Decisões abertas

Nenhuma. Todas as decisões de escopo, arquitetura, modelo e UI foram tomadas durante o brainstorm de 2026-04-20 e estão refletidas neste documento.

## 11. Próximos passos após aprovação deste spec

1. Hugo revisa e aprova este spec (ou pede ajustes inline).
2. Sistema invoca a skill `superpowers:writing-plans` para produzir um plano de implementação detalhado a partir deste design.
3. Plano de implementação vira as PRs do M1 em diante.

---

## Apêndice A — Correspondência entre descobertas e decisões

Este spec consolida o resultado de 10 perguntas de clarificação, 4 seções de design com aprovação incremental e análise dos 4 artefatos reais enviados por Hugo (PP Bertioga 02/26, extrato Bradesco 12/04, orçamento abril/26, extrato Unicred 22/03-20/04).

Artefatos analisados em 2026-04-20:
- `/Users/dr.damasceno/Downloads/SPM - FB - Bertioga - 02.26 - Claude.xlsx`
- `/Users/dr.damasceno/Downloads/EXTRATO_POR_PERIODO_120426_221307.ofx`
- `/Users/dr.damasceno/Downloads/SPM - Orcamento - 04.2026.xlsx`
- `/Users/dr.damasceno/Downloads/Comp-20042026014849.pdf`

Achados críticos que moldaram o design:
- Orçamento XLSX é mini-DRE em 6 seções, não simples lista
- Extrato Unicred vem em PDF "para simples conferência", não OFX
- Conta Unicred mistura despesas empresa + pessoais + intercompany
- Hugo anota "Valor Pago" e "Data" à mão no XLSX — substituir isso é o norte do projeto
- Empresa FD aparece no mesmo orçamento como dimensão; outras empresas (AHAPS, MedSupport) virão depois
