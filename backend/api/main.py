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
    excecao_pj,
    extratos,
    orcamento,
    regra_classificacao,
    rodadas,
    saldos,
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
app.include_router(saldos.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "spm-api"}
