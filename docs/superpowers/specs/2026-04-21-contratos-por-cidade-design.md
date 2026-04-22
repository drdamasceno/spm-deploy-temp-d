# Contratos por Cidade — Design

**Data:** 2026-04-21
**Autor:** Hugo + Claude (brainstorming session)
**Status:** Aprovado — pronto pra implementação
**Predecessor:** `2026-04-20-sistema-financeiro-v2-design.md` (Plano 4 já deployado em produção)

## Goal

Reformatar a aba `/contratos` pra entregar visão financeira real dos contratos operacionais da SPM, eliminando o artefato do parser atual que criou 115 "contratos" (1 por local_pp distinto) e consolidando em **1 contrato = 1 cidade**. Inclui carry-over de saldos de competências anteriores com alertas por idade.

Desbloqueia 90% do controle financeiro que Hugo precisa. Crítico: sem isto, operação atual (fev/26, 12 dias pra quitar) continua cega à agregação por cidade.

## Escopo

- Reescrita do modelo de contrato: 1 linha por (uf, cidade).
- Consolidação dos 115 contratos atuais em 15 contratos-cidade via migration agregadora (preserva 374 registros_pp + rodada `22f82135-cf5b-487c-a916-6f504f2d930d` + conciliações existentes).
- Parser PP atualiza comportamento de upsert.
- UI `/contratos` nova: lista da competência atual + bloco collapsible de competências anteriores com saldo > 0, com 3 níveis de destaque por idade.
- UI `/contratos/[id]/[competencia]` reformatada: agregado por `(prestador × local × competência)` com colunas Competência | Local | Total | Pago | Saldo | Status | Data Pagamento.
- Editor de campos extras do contrato (CNPJ, nome_oficial, tipo, valor_faturamento_mensal, retencao_tributaria_pct, observacoes) na tab "Dados do contrato".

## Fora de escopo

- Track B (nova natureza "Despesas Hugo" no orçamento) — brainstorm separado pendente.
- Track D (saldos manuais no Dashboard).
- Fix do parser Unicred CID:X como titular + validação anti-regra-lixo no POST /conciliacoes (Track A.3) — vai junto do deploy mas código separado.
- Refactor do modelo de `orcamento_linha.contrato_id` (continua apontando pro UUID do contrato; agora cada contrato representa 1 cidade e não 1 local).

## Decisões

### Modelo de dados

**1 contrato = 1 (uf, cidade).** Hugo confirmou explicitamente: os 115 "contratos" atuais são artefato do parser que considera cada unidade de atendimento como contrato separado. Realidade: contrato é acordo com a cidade; dentro dela podem existir N locais de atendimento.

### Schema

**`contrato` ganha:**
- `uf text NOT NULL` — sigla 2 chars (SP, MG, PR)
- `cidade text NOT NULL` — nome em caixa alta (IGUAPE, UNAI)
- `nome_oficial text` — "Prefeitura Municipal de Iguape" (detalhe)
- `valor_faturamento_mensal numeric` — (detalhe)
- `retencao_tributaria_pct numeric` — (detalhe)
- `observacoes text` — (detalhe)
- `UNIQUE (uf, cidade)`

**`contrato` perde:**
- `local_pp` — deixa de ser chave do contrato; passa pra `registro_pp`

**`registro_pp` ganha:**
- `local_pp text` — preserva o sub-local exato (UBS RURAL, CAPS PSIQUIATRIA, etc.) pro detalhe da tela.

### Migração dos 115 contratos atuais (abordagem β agregadora)

Algoritmo:

1. Parsear `local_pp` de cada um dos 115 contratos atuais, normalizando separadores (`–` → `-`) e extraindo UF + cidade.
2. Normalizar acentos no lookup (`SERTÃOZINHO` = `SERTAOZINHO`) mas preservar grafia original pro display.
3. Para cada `(uf, cidade)` único, escolher o menor `id` como "principal".
4. `UPDATE registro_pp SET contrato_id = principal WHERE contrato_id IN (duplicados)`.
5. `UPDATE registro_pp SET local_pp = c.local_pp FROM contrato c WHERE registro_pp.contrato_id = c.id` (backfill de local_pp a partir do contrato original).
6. `DELETE FROM contrato WHERE id IN (duplicados não-principais)`.
7. `ALTER TABLE contrato ADD CONSTRAINT unique_uf_cidade UNIQUE (uf, cidade)`.
8. `ALTER TABLE contrato DROP COLUMN local_pp`.

**Resultado esperado:** 115 → 15 contratos consolidados. Nenhum `registro_pp` perdido. Todas as conciliações existentes (`conciliacao_orcamento`, `transacao_bancaria.registro_pp_id`) apontam pra `registro_pp` que continua com mesmo `id`, só muda o `contrato_id`.

### Parser PP (workflow: auto-criação + edição depois)

Refactor de `backend/api/routers/rodadas.py:_garantir_contrato`:

- Input: string `Local` do XLSX (ex: `"SP - IGUAPE - UBS RURAL - ESF - SPM"`)
- Normalizar separadores (`–` → `-`)
- Split por ` - `:
  - `uf = parts[0]` (uppercase, 2 chars)
  - `cidade = parts[1]` (uppercase)
  - `local_pp_sub = " - ".join(parts[2:])` (guarda no registro_pp)
- Lookup `contrato` por `(uf, cidade_normalizada_sem_acento)`. Se existe, retorna `id`. Se não, insere novo com `tipo='PUBLICO'` hardcoded (Hugo edita os campos extras depois na tela de detalhe).
- Retorna `contrato_id` + `local_pp_sub` pro persistidor do registro_pp.

### Motor de cálculo (Total / Pago / Saldo / Status / Data Pagamento)

- **Total** = `registro_pp.saldo_pp` (saldo bruto do PP no momento do upload, snapshot imutável, já com taxas deduzidas — [ANCORADA] do vault)
- **Total Pago** = `SUM(ABS(transacao_bancaria.valor))` onde `registro_pp_id` aponta pro registro (base própria SPM alimentada por extratos)
- **Saldo** = Total − Total Pago
- **Status** — derivado:
  - `Pago` quando `Total Pago ≥ Total`
  - `Parcial` quando `0 < Total Pago < Total`
  - `Pendente` quando `Total Pago = 0`
- **Data Pagamento** = `MAX(data_extrato)` dos PIX conciliados (data do PIX mais recente)
- **Idade em dias** (carry-over) = `CURRENT_DATE - last_day(mes_competencia)`

### Endpoints

| Método | Endpoint | Ação |
|---|---|---|
| GET | `/contratos?competencia=YYYY-MM` | Lista contratos-cidade agregados na competência; retorna `{id, uf, cidade, competencia, total, total_pago, saldo, prestadores, status}` |
| GET | `/contratos/anteriores?ate=YYYY-MM` | Carry-over: cidades com saldo > 0 em competências < ate, com `idade_dias` |
| GET | `/contratos/{id}/competencia/{mes}` | Detalhe: KPIs + lista `(prestador × local × competência)` agregada |
| PATCH | `/contratos/{id}` | Editar campos extras (CNPJ, nome_oficial, tipo, valor_faturamento_mensal, retencao_tributaria_pct, observacoes) |

### UI

**Tela lista** (`/contratos?competencia=04.26`) — referência: mockup v4 em `.superpowers/brainstorm/.../contratos-mockup-v4-age-alerts.html`:

- Bloco 1 "Contratos de 04.26": cabeçalho azul, tabela com colunas Contrato | Prest. | Total | Pago | Saldo | Status.
- Bloco 2 "Competências anteriores em aberto": **collapsible** (fechado por default), header com gradient indigo claro + barra lateral violeta `#4f46e5`, mostra contagem + valor total à direita.
- Quando expandido: sub-grupos por competência (mais recente primeiro), com 3 níveis de destaque:
  - **≤ 60 dias**: tom neutro (indigo claro, rótulo "N dias em aberto")
  - **60-90 dias**: **laranja** (gradient `#fed7aa → #fef3c7`, ⏱, caps "N DIAS EM ABERTO", texto "atenção — 60+ dias")
  - **90+ dias**: **vermelho** (gradient `#fca5a5 → #fecaca`, ⚠️, caps "URGENTE", badge escuro "90+ DIAS")
- **Sem cap de meses.** Lista todas as competências com saldo > 0.
- Rodapé com faixa preta: "Total em aberto (atual + anteriores) = R$ X".

**Tela detalhe** (`/contratos/{id}/competencia/{mes}`):

- Breadcrumb + tabs: "Pagamentos" (default) | "Dados do contrato"
- 4 KPIs: Total (destaque preto) | Pago | Saldo (vermelho) | Prestadores (N · M registros)
- Tabela: Competência | Prestador | Local | Total | Pago | Saldo | Status | Data Pagamento
- Tab "Dados do contrato": formulário com CNPJ, nome_oficial, tipo (select PUBLICO/PRIVADO), valor_faturamento_mensal, retencao_tributaria_pct, observacoes — saves via `PATCH /contratos/{id}`.

## Plano de implementação

1. Migration 0010 (adicionar colunas + backfill + consolidação + UNIQUE + DROP local_pp).
2. Refactor parser `rodadas.py:_garantir_contrato`.
3. Refactor router `contratos_competencia.py` (query agrupada + endpoint /anteriores + PATCH /contratos).
4. Ajustar schemas Pydantic (`backend/api/schemas/contrato_competencia.py`) + types frontend (`frontend/types/v2.ts`).
5. Refactor `frontend/app/(authed)/contratos/page.tsx` (lista + carry-over collapsible com 3 níveis).
6. Refactor `frontend/app/(authed)/contratos/[id]/[competencia]/page.tsx` (tabs + tabela agregada + editor).
7. Testes: pytest pra parser novo + motor de cálculo + 2-3 integrations testando os 3 endpoints.
8. Deploy via snapshot-temp (mesmo fluxo do M5-B).
9. Smoke em prod: lista 15 contratos, expande carry-over, detalhe UNAI, edita CNPJ de 1 contrato.

**Paralelismo:** tasks 1-4 serialmente (dependem); tasks 5+6 em paralelo (frontend independente); task 7 em paralelo com 5/6; task 8 depende de tudo.

**Tempo estimado:** ~4-5h real com subagents rodando em paralelo.

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Migration consolida contratos errados (ex: 2 cidades com mesma grafia diferenciadas por acento) | Normalização de acento no `GROUP BY` mas preservação da grafia na coluna `cidade`. Executar a migration dentro de `BEGIN/ROLLBACK` pra validar antes de commit |
| `registro_pp.contrato_id` muda pra id "principal" — risco de órfão se ordem de DELETE errada | Migration é transacional; UPDATE antes de DELETE; validação pós-migration: `SELECT COUNT(*) FROM registro_pp WHERE contrato_id NOT IN (SELECT id FROM contrato)` deve retornar 0 |
| `orcamento_linha.contrato_id` aponta pra contratos deletados | Orçamento atual (04.26) foi deletado no Track A.1; novos orçamentos vão apontar pros IDs agregados novos. Zero órfãos |
| Deploy via snapshot temp expõe repo público novamente | Workflow validado no M5-B; temp repo deletado manualmente pelo Hugo após deploy (scope `delete_repo` no gh token) |
| UI carry-over fica confusa com muitas competências | Default collapsed resolve; se Hugo reclamar, adicionar busca/filtro dentro do bloco |
| Cálculo de idade_dias em timezone divergente | Usar `CURRENT_DATE AT TIME ZONE 'America/Sao_Paulo'` explicitamente |

## Integração com memória ancorada do vault

- **[ANCORADA] saldo_pp** já tem taxas deduzidas — design respeita (não recalcula; usa `saldo_pp` direto como Total).
- **[ANCORADA] local_pp** era a chave de match PP→contrato. Agora passa a viver em `registro_pp.local_pp` (preservado, não perdido). Chave de match PP→contrato vira `(uf, cidade)` derivado.
- **[ANCORADA] Total Pago** vem da base própria SPM (não do PP). Design usa `SUM(ABS(transacao_bancaria.valor))` via `registro_pp_id` — coerente.
- **Defasagem de pagamentos** (competência ≠ mês de pagamento) — carry-over resolve visualização.

## Links

- Mockup visual aprovado: `.superpowers/brainstorm/5588-1776812186/content/contratos-mockup-v4-age-alerts.html`
- Rodada operacional em uso: `22f82135-cf5b-487c-a916-6f504f2d930d` (competência 2026-02, status CONCILIADA)
- Deploy atual: `https://spm-financeiro-web.onrender.com` + `https://spm-financeiro-api.onrender.com`
