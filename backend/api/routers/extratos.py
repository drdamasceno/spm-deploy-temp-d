from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.extrato import UploadExtratoResponse
from backend.src.persistencia_parsers import (
    persistir_extrato_bradesco,
    persistir_extrato_unicred,
)


router = APIRouter(prefix="/extratos", tags=["extratos"])


@router.post("/unicred/upload", response_model=UploadExtratoResponse, status_code=status.HTTP_201_CREATED)
def upload_unicred(
    conta_id: UUID = Form(...),
    arquivo: UploadFile = File(...),
    current=Depends(get_current_user),
):
    client = get_supabase_authed(current["jwt"])
    pdf_bytes = arquivo.file.read()
    try:
        return persistir_extrato_unicred(client, pdf_bytes, conta_id)
    except ValueError as e:
        raise HTTPException(400, detail={"error": str(e)})


@router.post("/bradesco/upload", response_model=UploadExtratoResponse, status_code=status.HTTP_201_CREATED)
def upload_bradesco(
    arquivo: UploadFile = File(...),
    current=Depends(get_current_user),
):
    client = get_supabase_authed(current["jwt"])
    ofx_bytes = arquivo.file.read()
    try:
        return persistir_extrato_bradesco(client, ofx_bytes)
    except ValueError as e:
        raise HTTPException(400, detail={"error": str(e)})
