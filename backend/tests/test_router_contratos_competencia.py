import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SERVICE_ROLE_KEY ausente",
)


def test_view_contrato_competencia_retorna_dre(client, ceo_headers, service_role_client):
    """
    Usa dados do seed real: escolhe um contrato com registro_pp em 2026-02 e valida a estrutura.
    """
    # Pega um contrato qualquer que tenha pelo menos um registro_pp em 2026-02
    rpps = service_role_client.table("registro_pp").select("contrato_id").eq("mes_competencia", "2026-02").limit(1).execute().data
    if not rpps:
        pytest.skip("Sem registro_pp em 2026-02 — seed não disponível")
    contrato_id = rpps[0]["contrato_id"]

    r = client.get(f"/contratos/{contrato_id}/competencia/2026-02", headers=ceo_headers)
    assert r.status_code == 200, r.text
    data = r.json()

    # Estrutura mínima
    assert data["contrato_id"] == contrato_id
    assert data["competencia"] == "2026-02"
    assert "nome_contrato" in data
    assert "total_devido" in data
    assert "total_pago" in data
    assert "percentual_pago" in data
    assert isinstance(data["prestadores"], list)

    # Validações lógicas
    assert data["total_devido"] >= 0
    assert data["total_pago"] >= 0
    if data["total_devido"] > 0:
        assert 0 <= data["percentual_pago"] <= 100

    # Telemetria para reporte do subagent
    print(
        f"\n[TELEMETRIA] contrato={contrato_id} "
        f"prestadores={len(data['prestadores'])} "
        f"total_devido={data['total_devido']} "
        f"total_pago={data['total_pago']} "
        f"percentual_pago={data['percentual_pago']}"
    )


def test_view_contrato_inexistente_retorna_404(client, ceo_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(f"/contratos/{fake_id}/competencia/2026-02", headers=ceo_headers)
    assert r.status_code == 404


def test_view_competencia_formato_invalido(client, ceo_headers, service_role_client):
    contrato_id = service_role_client.table("contrato").select("id").limit(1).execute().data[0]["id"]
    r = client.get(f"/contratos/{contrato_id}/competencia/invalido", headers=ceo_headers)
    assert r.status_code == 400
