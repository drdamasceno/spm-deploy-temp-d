# SPM Sistema Financeiro — API

Backend FastAPI do Sistema Financeiro SPM. Camada de autenticacao (Bloco A do Passo 3).

## Setup

```bash
cd ~/spm-sistemafinanceiro
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# editar backend/.env e preencher SUPABASE_ANON_KEY
```

## Rodar

```bash
source backend/.venv/bin/activate
uvicorn backend.api.main:app --reload --port 8000
```

Docs em http://localhost:8000/docs

## Endpoints (Bloco A)

### POST /auth/login

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dr.damasceno@spmbr.com","password":"SpmTroca2026!"}'
```

Response 200:
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": {"id": "09ac0652-...", "email": "dr.damasceno@spmbr.com"}
}
```

### POST /auth/refresh

```bash
curl -s -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

### GET /auth/me

```bash
curl -s http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"
```

Response 200:
```json
{
  "id": "09ac0652-...",
  "email": "dr.damasceno@spmbr.com",
  "nome": "Hugo Damasceno",
  "role": "CEO"
}
```

## Arquivos

- `main.py` — app FastAPI, CORS, mount do router `/auth`
- `deps.py` — Settings (pydantic-settings) + clients Supabase (anon e autenticado) + `get_current_user`
- `routers/auth.py` — 3 endpoints
- `schemas/auth.py` — pydantic models
