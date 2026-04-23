# SPM Sistema Financeiro — Guia para Claude Code

## Repositórios

- Backend: ~/spm-sistemafinanceiro/backend
- Frontend: ~/spm-sistemafinanceiro/frontend

## Stack

- Backend: Python + FastAPI + Supabase via httpx
- Frontend: React + TypeScript + TailwindCSS + shadcn/ui
- Banco: PostgreSQL via Supabase (projeto: mkxehqhikcuykaxnpxff)
- Deploy: Render (backend) + Lovable ou Vercel (frontend)

## Regras invioláveis

1. Coluna de contrato no Pega Plantao = "Local" (não "Setor")
2. Saldo do PP já tem taxas deduzidas — NUNCA recalcular
3. Match válido exige titular PIX = nome_prestador ou razao_social_pj cadastrada
4. NUNCA conciliar por valor coincidente sem titularidade confirmada
5. Pagamentos apenas segundas e quintas
6. Hugo é o único aprovador final — nenhum pagamento sem autorização dele
7. Sem NFE = sem pagamento

## Arquivos críticos

- backend/src/pega_plantao.py — parser PP XLSX (fonte de verdade)
- backend/src/extrato_bradesco.py — parser extrato Bradesco OFX
- backend/src/conciliacao_spm.py — motor de conciliação (match automático, fracionado, exceções PJ)
- backend/src/excel_builder.py — gerador de relatórios (reaproveitado do FaturaAI)
- backend/conciliar_spm.py — CLI principal com geração de XLSX colorido

## Como executar localmente

### Pré-requisitos

```bash
cd ~/spm-sistemafinanceiro
git pull
pip install openpyxl
```

### Executar conciliação com arquivos reais

```bash
python backend/conciliar_spm.py \
  "/mnt/user-data/uploads/SPM_-_FB_-_Conf__01_a_09_04_2026_Claudexlsx.xlsx" \
  "/mnt/user-data/uploads/EXTRATO_POR_PERIODO_120426_221307.ofx"
```

### Script completo (setup + testes + execução)

```bash
bash backend/setup_e_roda.sh
```

### Executar testes unitários

```bash
python backend/tests/teste_pega_plantao.py
python backend/tests/teste_extrato_bradesco.py
python backend/tests/teste_integracao.py   # testa pipeline completo com dados sintéticos
```

### Diagnóstico (inspeção de arquivos + conciliação)

```bash
python backend/diagnostico_e_concilia.py
```

## Estrutura do PP XLSX

- Linhas 1-3: cabeçalho global (ignoradas)
- Linha vazia: separa blocos de prestadores
- Por bloco:
  - Linha A: "NOME PRESTADOR  -  CRM/UF"
  - Linha B: "Transação: PIX  Tipo de Documento: CPF/CNPJ  Chave Pix: XXX  Documento: XXX  Razão social: NOME"
  - Linha C: cabeçalho colunas (Data, Local, Tipo, Duração, Valor, Total, Total Pago, Saldo)
  - Linhas D+: plantões
  - Linha "Total": Saldo da coluna H = saldo_final do prestador+contrato

## Estrutura do Extrato OFX

- Formato: SGML OFX 1.02, encoding latin-1/cp1252
- Banco: BANKID 0237 (Bradesco)
- Cada transação: `<STMTTRN>...<TRNTYPE>...<DTPOSTED>...<TRNAMT>...<MEMO>...</STMTTRN>`

## Exceções PJ (validadas por Hugo)

```json
{
  "CLINICA DR FABIO": "FABIO",
  "GLENIO S": "GLENIO",
  "LUANA": "NAYARA"
}
```

Use via: `python backend/conciliar_spm.py ... --excecoes excecoes.json`

## Status atual

- Fase 0: parsers + motor de conciliação local ✅
- Passo 3: API FastAPI em backend/api/ (auth + upload de rodada) ✅
- Passo 5a: motor integrado na API, 93,04% conciliação na rodada 22f82135 ✅
- Bloco D: CRUD excecao_pj + rodada_snapshot (migration 0005 aplicada) ✅
  - Pendente: pytest dos 12 casos + smoke test manual
- Bloco E: pagamentos e validação (próximo)
- Frontend: Next.js 16 (pendente validação do Bloco D)

## Limites de escopo: software vs jurídico-contábil

Este repositório implementa a camada de **software** (visualização, controle de caixa, conciliação, dashboards). NÃO implementa camada jurídico-contábil.

**O sistema faz:**
- Separar bolsos financeiros (SPM operacional / FD via SPM / Hugo pessoal / investimento) como dimensão gerencial
- Split de transações (ex: fatura cartão metade SPM / metade pessoal)
- Vincular prestador a PJ empregadora (evita duplicidade CLT FD ↔ PP)
- Dashboard consolidador acima das entidades

**O sistema NÃO faz:**
- Emitir NFE
- Escriturar livros contábeis por CNPJ (responsabilidade do Fortcon)
- Formalizar contratos inter-company (SPM↔FD) ou mútuo com sócio (SPM↔Hugo PF)
- Gerar apurações tributárias

**Recomendações jurídico-contábeis:** ver `~/second-brain/dominios/spm/recomendacoes-juridico-contabeis.md`. Contratos pendentes (conta corrente SPM↔FD, mútuo SPM↔Hugo PF, política formal de distribuição de lucros) são responsabilidade de advogado tributarista + Fortcon. O desenho de features no software **não depende** desses contratos estarem assinados — o software opera independentemente.

**Regra:** quando surgir tema jurídico-contábil durante desenvolvimento, apontar para a nota do vault e manter foco no software.

## Estrutura do backend web

- backend/api/main.py — entrypoint FastAPI (sem prefix /api; rotas diretas: /auth, /rodadas, /excecoes_pj)
- backend/api/deps.py — Settings + get_current_user + require_ceo + require_ceo_with_2fa
- backend/api/routers/ — auth.py, rodadas.py, excecao_pj.py
- backend/api/schemas/ — pydantic v2, arquivo por domínio
- backend/supabase/migrations/ — 0005 é a última; 0006+ para endurecimentos (pgcrypto, RPC fn_aprovar_rodada)
- backend/supabase/ — projeto Supabase mkxehqhikcuykaxnpxff COMPARTILHADO
  com FaturaAI (projetos paralelos, apenas infra Supabase em comum).
  Ao consultar information_schema, sempre filtrar por tabela específica.
