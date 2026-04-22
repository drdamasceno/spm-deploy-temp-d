import os
from pathlib import Path
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SERVICE_ROLE_KEY ausente",
)

FIXTURE = Path(__file__).parent / "fixtures" / "SPM_Orcamento_04_2026.xlsx"


def test_upload_orcamento_cria_linhas(client, ceo_headers, request):
    r = client.get("/empresas", headers=ceo_headers)
    spm_id = next(e["id"] for e in r.json() if e["codigo"] == "SPM")
    with open(FIXTURE, "rb") as f:
        r = client.post(
            "/orcamentos/upload",
            headers=ceo_headers,
            data={"empresa_id": spm_id, "competencia": "2099-11"},
            files={"arquivo": ("orcamento.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["total_linhas_inseridas"] > 100
    assert data["linhas_por_secao"]["DESPESA_FIXA"] > 30
    orcamento_id = data["orcamento_id"]
    request.addfinalizer(lambda: client.delete(f"/orcamentos/{orcamento_id}", headers=ceo_headers))


def test_upload_orcamento_duplicado_rejeita(client, ceo_headers):
    r = client.get("/empresas", headers=ceo_headers)
    spm_id = next(e["id"] for e in r.json() if e["codigo"] == "SPM")
    with open(FIXTURE, "rb") as f:
        client.post("/orcamentos/upload", headers=ceo_headers,
                    data={"empresa_id": spm_id, "competencia": "2099-10"},
                    files={"arquivo": ("o.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    with open(FIXTURE, "rb") as f:
        r = client.post("/orcamentos/upload", headers=ceo_headers,
                        data={"empresa_id": spm_id, "competencia": "2099-10"},
                        files={"arquivo": ("o.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 409
    resp_orcamento = client.get(f"/orcamentos?empresa_id={spm_id}&competencia=2099-10", headers=ceo_headers)
    if resp_orcamento.status_code == 200 and resp_orcamento.json():
        client.delete(f"/orcamentos/{resp_orcamento.json()[0]['id']}", headers=ceo_headers)
