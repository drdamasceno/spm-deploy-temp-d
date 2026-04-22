# Saldos no Dashboard — Design (Track D)

**Data:** 2026-04-21
**Status:** Aprovado

## Goal

Tile novo no topo do Dashboard mostrando liquidez da SPM: contas correntes (auto via parser de extrato) + aplicações financeiras (input manual). Split visual: "Disponível agora" (contas + aplicações automáticas) vs "Reserva travada" (aplicações manuais).

## Decisões

### Semântica Auto/Manual em aplicações

- **Automática:** vinculada à conta corrente, entra/sai sozinha (varredura overnight, CDB liquidez diária). Conta como liquidez disponível.
- **Manual:** travada, requer ação pra aplicar/resgatar (CDB prazo fixo, Tesouro, FII, LCI/LCA com carência). Reserva imobilizada.

### Schema

**`saldo_conta_snapshot`** (nova):
- id, conta_bancaria_id (FK), saldo_valor numeric(14,2), data_referencia date, origem enum('BRADESCO_OFX' | 'UNICRED_PDF' | 'MANUAL'), observacao text, criado_em, criado_por
- Guarda todos os snapshots (historical). Dashboard usa o mais recente por conta via query DISTINCT ON.

**`aplicacao_financeira`** (nova):
- id, nome text NOT NULL, tipo enum tipo_aplicacao, valor_atual numeric(14,2), data_atualizacao date, modo enum('AUTOMATICA'|'MANUAL'), instituicao text, rentabilidade text, data_vencimento date, liquidez enum('DIARIA'|'VENCIMENTO'|'D30'|'D90'|'D180'), observacoes text, ativo bool, criado_em, updated_em

**Enum `tipo_aplicacao`:** CDB, LCA, LCI, FUNDO, POUPANCA, TESOURO, ACOES, FII, OUTROS

**`aplicacao_historico`** (nova — snapshots de valor):
- id, aplicacao_id (FK), valor, data_snapshot, criado_por

### Parsers

- **Bradesco OFX** (`extrato_bradesco.py`): extrair `<LEDGERBAL><BALAMT>` + `<DTASOF>` (data de referência). Retornar `ExtratoBradesco` com `saldo_final` e `data_saldo`.
- **Unicred PDF** (`extrato_unicred.py`): já extrai `saldo_final` via regex. Adicionar `data_saldo` (do header). Fix bug: limpar `(cid:\d+)` antes de extrair titular (Task A.3 combinada).

### Upload flow

No endpoint de upload de rodada (`rodadas.py`), após salvar transações, chamar `salvar_saldo_snapshot(conta_bancaria_id, saldo, data_referencia, origem)`.

### Endpoints

- `GET /saldos/dashboard` → `{ contas: [...], aplicacoes: [...], total_liquidez, disponivel_agora, reserva_travada }`
- `POST /saldos/conta-manual` → snapshot manual de conta corrente
- `GET /aplicacoes`
- `POST /aplicacoes`
- `PATCH /aplicacoes/{id}`
- `DELETE /aplicacoes/{id}` (soft-delete via `ativo=false`)

### UI

- Novo componente `<LiquidezBanner />` no topo do `/` (Dashboard atual), acima dos KPIs existentes.
- 2 colunas lado a lado: `<ContasCorrentesSection />` + `<AplicacoesSection />`.
- Modal `<EditorAplicacaoDialog />` pra create/edit.

## Plano de implementação

1. Migration 0011 (schema) + apply via MCP
2. Parser Bradesco expõe saldo
3. Parser Unicred expõe data_saldo + fix CID
4. Upload salva snapshot
5. Schemas Pydantic novos
6. Endpoints `/saldos/*` e `/aplicacoes`
7. Types frontend + api client
8. Componentes UI
9. Integrar no Dashboard
10. Deploy via snapshot-temp
