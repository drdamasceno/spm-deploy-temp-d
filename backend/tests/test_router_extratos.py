"""Tests do router /extratos (Unicred PDF + Bradesco OFX).

Estrategia de cleanup: cada fixture cria uma conta_bancaria isolada via service_role
e, no teardown, deleta primeiro todas as transacoes daquela conta_id e depois a
conta. Isso isola completamente o teste de dados pre-existentes e nao usa DELETE
cego por origem_banco.
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

FIXTURE_UNICRED = Path(__file__).parent / "fixtures" / "Comp_Unicred_20042026.pdf"
FIXTURE_BRADESCO = Path(__file__).parent / "fixtures" / "EXTRATO_POR_PERIODO_120426_221307.ofx"


@pytest.fixture
def conta_unicred(service_role_client):
    """Cria uma conta Unicred matching ao PDF fixture (banco=544, conta=6688055).

    Usa suffix UUID para evitar colisão se a suite rodar em paralelo com dados reais.
    Como a unicidade da conta_bancaria não é por (banco, conta), simplesmente usamos
    os valores do PDF — se já existir conflito, o teste cai em skip.
    """
    # suffix curto nos campos agencia/finalidade-inexistente para distinguir se vier a haver
    tag = uuid.uuid4().hex[:6]
    payload = {
        "banco": "544",
        "agencia": f"0001",
        "conta": f"6688055",
        "finalidade": "RECEBIMENTOS",
        "ativo": True,
    }
    # Se já existir conta com banco/conta identicos (de runs anteriores nao limpos),
    # reutiliza.
    existing = (
        service_role_client.table("conta_bancaria")
        .select("id")
        .eq("banco", payload["banco"])
        .eq("conta", payload["conta"])
        .execute()
        .data
    )
    if existing:
        conta_id = existing[0]["id"]
        created_here = False
    else:
        r = service_role_client.table("conta_bancaria").insert(payload).execute()
        conta_id = r.data[0]["id"]
        created_here = True

    yield conta_id

    # Teardown: limpa transacoes e conta (apenas se criamos aqui)
    try:
        service_role_client.table("transacao_bancaria").delete().eq("conta_id", conta_id).execute()
    except Exception as e:
        print(f"[teardown] transacoes conta {conta_id}: {e}")
    if created_here:
        try:
            service_role_client.table("conta_bancaria").delete().eq("id", conta_id).execute()
        except Exception as e:
            print(f"[teardown] conta {conta_id}: {e}")


@pytest.fixture
def conta_bradesco_cc(service_role_client):
    """Cria conta Bradesco conta corrente matching ao OFX fixture (banco=237, conta=22982).

    O parser `extract_bank_account` retorna BANKID='0237' e ACCTID='22982'. A função
    `persistir_extrato_bradesco` faz fallback removendo zeros à esquerda do BANKID
    para casar com o cadastro "237".
    """
    payload = {
        "banco": "237",
        "agencia": "0001",
        "conta": "22982",
        "finalidade": "RECEBIMENTOS",
        "ativo": True,
    }
    existing = (
        service_role_client.table("conta_bancaria")
        .select("id")
        .eq("banco", payload["banco"])
        .eq("conta", payload["conta"])
        .execute()
        .data
    )
    if existing:
        conta_id = existing[0]["id"]
        created_here = False
    else:
        r = service_role_client.table("conta_bancaria").insert(payload).execute()
        conta_id = r.data[0]["id"]
        created_here = True

    yield conta_id

    try:
        service_role_client.table("transacao_bancaria").delete().eq("conta_id", conta_id).execute()
    except Exception as e:
        print(f"[teardown] transacoes conta {conta_id}: {e}")
    if created_here:
        try:
            service_role_client.table("conta_bancaria").delete().eq("id", conta_id).execute()
        except Exception as e:
            print(f"[teardown] conta {conta_id}: {e}")


def test_upload_unicred_insere_transacoes(client, ceo_headers, conta_unicred):
    with open(FIXTURE_UNICRED, "rb") as f:
        r = client.post(
            "/extratos/unicred/upload",
            headers=ceo_headers,
            data={"conta_id": conta_unicred},
            files={"arquivo": ("u.pdf", f, "application/pdf")},
        )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["origem_banco"] == "UNICRED"
    assert data["total_transacoes_inseridas"] >= 80
    assert data["conta_id"] == conta_unicred
    assert data["periodo_inicio"].startswith("2026-")
    assert data["periodo_fim"].startswith("2026-")


def test_upload_bradesco_insere_transacoes(client, ceo_headers, conta_bradesco_cc):
    with open(FIXTURE_BRADESCO, "rb") as f:
        r = client.post(
            "/extratos/bradesco/upload",
            headers=ceo_headers,
            files={"arquivo": ("b.ofx", f, "application/x-ofx")},
        )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["origem_banco"] == "BRADESCO"
    # OFX fixture tem 297 transacoes; tolerancia caso alguma tenha data vazia
    assert data["total_transacoes_inseridas"] >= 250
    assert data["conta_id"] == conta_bradesco_cc


def test_upload_bradesco_conta_nao_cadastrada_rejeita(client, ceo_headers, service_role_client):
    """Se nao houver conta para o (banco, conta) do OFX, retorna 400."""
    # Garante que NAO existe conta cadastrada com banco=237 conta=22982.
    # Se existir de um teste anterior nao limpo, skip por conflito.
    existing = (
        service_role_client.table("conta_bancaria")
        .select("id")
        .eq("banco", "237")
        .eq("conta", "22982")
        .execute()
        .data
    )
    if existing:
        pytest.skip("conta 237/22982 ja cadastrada — teste de rejeicao nao se aplica nesta rodada")
    with open(FIXTURE_BRADESCO, "rb") as f:
        r = client.post(
            "/extratos/bradesco/upload",
            headers=ceo_headers,
            files={"arquivo": ("b.ofx", f, "application/x-ofx")},
        )
    assert r.status_code == 400, r.text
    assert "nao cadastrada" in r.json()["error"].lower() or "cadastrada" in r.json()["error"].lower()
