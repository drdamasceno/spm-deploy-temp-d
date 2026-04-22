"""E2E do router /conciliacoes.

Cenario:
  1. Cria conta Unicred + upload de orcamento SPM (competencia 2099-11 fora
     do calendario real para nao colidir) + upload PDF Unicred.
  2. GET /conciliacoes/sugestoes -> espera >= 1 sugestao.
  3. Aplica uma sugestao NAO-REGRA via POST -> confere que criou
     regra_classificacao ativa com titular_pix_padrao correspondente.
  4. Consulta novamente -> confirma que a regra foi efetivada (pode aparecer
     origem=REGRA em outras transacoes do mesmo titular; se nao houver, so
     valida que a regra foi criada).
  5. DELETE /conciliacoes/{id} -> confere que transacao volta a NAO_CLASSIFICADO.
  6. Cleanup rigoroso em finalizer, filtrado pelos IDs criados neste teste.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SERVICE_ROLE_KEY ausente",
)

ORC_XLSX = Path(__file__).parent / "fixtures" / "SPM_Orcamento_04_2026.xlsx"
UNI_PDF = Path(__file__).parent / "fixtures" / "Comp_Unicred_20042026.pdf"


def test_conciliacao_e2e_com_aprendizado_de_regra(
    client, ceo_headers, service_role_client, request
):
    from backend.src.classificador_conciliacao import normalizar_titular

    # Tag unico por run para isolar conta e evitar colisao do UNIQUE (banco,agencia,conta)
    # se houver resto de rodada anterior. O fixture `conta_unicred` de extratos usa
    # (544,0001,6688055) — usamos agencia unica aqui para nao bater com ele.
    tag = uuid.uuid4().hex[:6]
    conta_payload = {
        "banco": "544",
        "agencia": f"99{tag[:4]}",   # unique agencia -> evita colisao
        "conta": f"6688055",
        "finalidade": "FIXAS",
        "ativo": True,
    }
    conta = service_role_client.table("conta_bancaria").insert(conta_payload).execute().data[0]
    conta_id = conta["id"]

    # Competencia com ano fake para isolar — uploader rejeita duplicata por
    # UNIQUE (empresa_id, competencia).
    competencia = f"2099-{(hash(tag) % 12) + 1:02d}"

    # Descobre empresa SPM
    r = client.get("/empresas", headers=ceo_headers)
    assert r.status_code == 200, r.text
    spm_id = next(e["id"] for e in r.json() if e["codigo"] == "SPM")

    # Upload orcamento
    with open(ORC_XLSX, "rb") as f:
        up = client.post(
            "/orcamentos/upload",
            headers=ceo_headers,
            data={"empresa_id": spm_id, "competencia": competencia},
            files={"arquivo": ("o.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert up.status_code == 201, up.text
    orcamento_id = up.json()["orcamento_id"]

    # Upload extrato Unicred
    with open(UNI_PDF, "rb") as f:
        ue = client.post(
            "/extratos/unicred/upload",
            headers=ceo_headers,
            data={"conta_id": conta_id},
            files={"arquivo": ("u.pdf", f, "application/pdf")},
        )
    assert ue.status_code == 201, ue.text

    # Estado compartilhado para o finalizer rastrear regras criadas.
    criados = {"regra_ids": [], "conciliacao_ids": []}

    def _cleanup():
        # Ordem: conciliacoes criadas neste teste -> regras -> transacoes da conta -> orcamento (cascade linhas) -> conta
        try:
            # Apaga qualquer conciliacao criada neste run
            if criados["conciliacao_ids"]:
                (
                    service_role_client.table("conciliacao_orcamento")
                    .delete()
                    .in_("id", criados["conciliacao_ids"])
                    .execute()
                )
            # Tambem apaga conciliacoes que possam ter sobrado referenciando transacoes desta conta
            tx_ids = [
                t["id"]
                for t in service_role_client.table("transacao_bancaria")
                .select("id").eq("conta_id", conta_id).execute().data
            ]
            if tx_ids:
                (
                    service_role_client.table("conciliacao_orcamento")
                    .delete()
                    .in_("transacao_id", tx_ids)
                    .execute()
                )
        except Exception as e:
            print(f"[teardown] conciliacao_orcamento: {e}")
        try:
            if criados["regra_ids"]:
                (
                    service_role_client.table("regra_classificacao")
                    .delete()
                    .in_("id", criados["regra_ids"])
                    .execute()
                )
        except Exception as e:
            print(f"[teardown] regra_classificacao: {e}")
        try:
            service_role_client.table("transacao_bancaria").delete().eq("conta_id", conta_id).execute()
        except Exception as e:
            print(f"[teardown] transacoes conta {conta_id}: {e}")
        try:
            # Cascade apaga orcamento_linha; FK em conciliacao_orcamento tem
            # ON DELETE RESTRICT para orcamento_linha, mas ja apagamos as conciliacoes acima
            service_role_client.table("orcamento").delete().eq("id", orcamento_id).execute()
        except Exception as e:
            print(f"[teardown] orcamento {orcamento_id}: {e}")
        try:
            service_role_client.table("conta_bancaria").delete().eq("id", conta_id).execute()
        except Exception as e:
            print(f"[teardown] conta {conta_id}: {e}")

    request.addfinalizer(_cleanup)

    # =========================================================================
    # Ato 1: sugestoes iniciais
    # =========================================================================
    r = client.get(
        f"/conciliacoes/sugestoes?orcamento_id={orcamento_id}&conta_id={conta_id}",
        headers=ceo_headers,
    )
    assert r.status_code == 200, r.text
    sugs = r.json()
    assert len(sugs) >= 1, f"Esperado >=1 sugestao, obtido {len(sugs)}: {sugs[:3]}"

    # Distribuicao por origem (util para reporte manual)
    por_origem = {}
    for s in sugs:
        por_origem[s["origem"]] = por_origem.get(s["origem"], 0) + 1
    print(f"[teste] Ato1 sugestoes: total={len(sugs)} por_origem={por_origem}")

    # Primeiro candidato nao-REGRA com titular_pix significativo (filtra
    # artefatos de PDF como 'cid:9'). Prefere SIMILARIDADE sobre VALOR pois
    # SIMILARIDADE garante nome batendo com a linha do orcamento.
    def _titular_util(tx_id: str) -> str | None:
        rows = (
            service_role_client.table("transacao_bancaria")
            .select("titular_pix")
            .eq("id", tx_id)
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            return None
        tp = rows[0].get("titular_pix") or ""
        # rejeita artefatos tipo 'cid:9', vazios, ou muito curtos
        if not tp or tp.lower().startswith("cid:") or len(tp.strip()) < 5:
            return None
        return tp

    def _prioridade(origem: str) -> int:
        return {"SIMILARIDADE": 0, "VALOR": 1, "MANUAL": 2}.get(origem, 3)

    candidatas = [
        s for s in sugs
        if s["origem"] != "REGRA" and _titular_util(s["transacao_id"])
    ]
    candidatas.sort(key=lambda s: (_prioridade(s["origem"]), -s["confianca"]))
    assert candidatas, (
        f"Esperado ao menos uma sugestao nao-REGRA com titular util; "
        f"origens={por_origem}"
    )
    primeira = candidatas[0]

    # =========================================================================
    # Ato 2: aplica conciliacao
    # =========================================================================
    payload = {
        "transacao_id": primeira["transacao_id"],
        "orcamento_linha_id": primeira["orcamento_linha_id"],
        "valor_aplicado": primeira["valor_aplicado"],
        "confianca": primeira["confianca"],
        "origem": primeira["origem"],
    }
    ap = client.post("/conciliacoes", headers=ceo_headers, json=payload)
    assert ap.status_code == 201, ap.text

    # Confere regra criada com o titular_pix normalizado
    titular_tx_rows = (
        service_role_client.table("transacao_bancaria")
        .select("titular_pix")
        .eq("id", primeira["transacao_id"])
        .limit(1)
        .execute()
        .data
    )
    assert titular_tx_rows, "transacao nao encontrada apos aplicar conciliacao"
    titular_tx = titular_tx_rows[0]
    assert titular_tx.get("titular_pix"), (
        f"esperado titular_pix na transacao aplicada; dados={titular_tx}"
    )
    titular_norm = normalizar_titular(titular_tx["titular_pix"])
    regras = (
        service_role_client.table("regra_classificacao")
        .select("*")
        .eq("titular_pix_padrao", titular_norm)
        .eq("ativa", True)
        .execute()
        .data
    )
    assert len(regras) == 1, (
        f"Esperado 1 regra ativa para titular {titular_norm!r}; obtido {len(regras)}: {regras}"
    )
    print(f"[teste] Regra aprendida: titular_pix_padrao={titular_norm!r}")
    criados["regra_ids"].extend([r["id"] for r in regras])

    # Rastrear a conciliacao criada para apagar no cleanup
    nova_conc = (
        service_role_client.table("conciliacao_orcamento")
        .select("id")
        .eq("transacao_id", primeira["transacao_id"])
        .eq("orcamento_linha_id", primeira["orcamento_linha_id"])
        .execute()
        .data
    )
    assert nova_conc, "conciliacao_orcamento nao foi persistida"
    criados["conciliacao_ids"].append(nova_conc[0]["id"])
    conciliacao_id = nova_conc[0]["id"]

    # Transacao deve estar MATCH_AUTOMATICO
    tx_status = (
        service_role_client.table("transacao_bancaria")
        .select("status_conciliacao")
        .eq("id", primeira["transacao_id"])
        .limit(1)
        .execute()
        .data[0]["status_conciliacao"]
    )
    assert tx_status == "MATCH_AUTOMATICO", tx_status

    # =========================================================================
    # Ato 3: sugestoes depois do aprendizado
    # =========================================================================
    r2 = client.get(
        f"/conciliacoes/sugestoes?orcamento_id={orcamento_id}&conta_id={conta_id}",
        headers=ceo_headers,
    )
    assert r2.status_code == 200, r2.text
    sugs2 = r2.json()

    # Se houver outra transacao do mesmo titular_pix pendente, a camada REGRA
    # deve pegar. Nao e garantido (pode ser a unica), entao o assert forte
    # e que a regra exista (ja verificado). Este print diagnostica o real.
    por_origem2 = {}
    for s in sugs2:
        por_origem2[s["origem"]] = por_origem2.get(s["origem"], 0) + 1
    print(f"[teste] Ato3 sugestoes pos-regra: total={len(sugs2)} por_origem={por_origem2}")

    # Verifica que a transacao aplicada nao aparece mais nas sugestoes
    # (ela ficou MATCH_AUTOMATICO e o motor so olha NAO_CLASSIFICADO).
    tx_ids_sug2 = {s["transacao_id"] for s in sugs2}
    assert primeira["transacao_id"] not in tx_ids_sug2, (
        "transacao aplicada nao deveria aparecer nas sugestoes pos-conciliacao"
    )

    # =========================================================================
    # Ato 4: desfaz conciliacao
    # =========================================================================
    rdel = client.delete(f"/conciliacoes/{conciliacao_id}", headers=ceo_headers)
    assert rdel.status_code == 204, rdel.text

    tx_status_reverse = (
        service_role_client.table("transacao_bancaria")
        .select("status_conciliacao")
        .eq("id", primeira["transacao_id"])
        .limit(1)
        .execute()
        .data[0]["status_conciliacao"]
    )
    assert tx_status_reverse == "NAO_CLASSIFICADO", (
        f"apos DELETE esperado NAO_CLASSIFICADO; obtido {tx_status_reverse}"
    )
    # ja apagamos a conciliacao pelo endpoint; tira do rastreamento para nao
    # tentar apagar de novo
    criados["conciliacao_ids"] = [
        cid for cid in criados["conciliacao_ids"] if cid != conciliacao_id
    ]
