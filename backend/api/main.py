import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.routers import (
    adiantamento,
    auth,
    catalogos,
    conciliacao,
    contratos_competencia,
    dashboard,
    dashboard_compromissos_recebiveis,
    dashboard_evolucao,
    dashboard_historico,
    dashboard_receita_financeira,
    dashboard_saidas_bolso,
    excecao_pj,
    extratos,
    orcamento,
    regra_classificacao,
    rodadas,
    saldos,
    transacao_linha,
)

load_dotenv()

app = FastAPI(
    title="SPM Sistema Financeiro API",
    version="0.1.0",
)

_cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def unwrap_error_detail(request: Request, exc: StarletteHTTPException):
    # Contrato do Bloco A: respostas de erro sao {"error": "..."} planas.
    # Quando detail e dict com chave "error", retorna sem embalar em {"detail": ...}.
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(rodadas.router, prefix="/rodadas", tags=["rodadas"])
app.include_router(excecao_pj.router, prefix="/excecoes_pj", tags=["excecoes_pj"])
app.include_router(catalogos.router, tags=["catalogos"])
app.include_router(orcamento.router)
app.include_router(extratos.router)
app.include_router(conciliacao.router)
app.include_router(regra_classificacao.router)
app.include_router(adiantamento.router)
app.include_router(contratos_competencia.router)
app.include_router(dashboard.router)
app.include_router(dashboard_evolucao.router)
app.include_router(dashboard_compromissos_recebiveis.router)
app.include_router(dashboard_receita_financeira.router)
app.include_router(dashboard_historico.router)
app.include_router(dashboard_saidas_bolso.router)
app.include_router(saldos.router)
app.include_router(transacao_linha.router)


@app.get("/version")
def version():
    """Retorna git commit do build. Útil pra confirmar qual deploy está live."""
    import subprocess
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ).decode().strip()
    except Exception:
        sha = os.environ.get("RENDER_GIT_COMMIT", "unknown")[:7]
    return {"commit": sha, "service": "spm-api"}


@app.get("/")
def root():
    return {"status": "ok", "service": "spm-api"}
