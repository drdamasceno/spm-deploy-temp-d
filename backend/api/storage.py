from __future__ import annotations

from fastapi import HTTPException, status
from supabase import Client


BUCKET_RODADAS = "rodadas"


def upload_to_supabase_storage(
    supabase: Client,
    bucket: str,
    path: str,
    file_content: bytes,
    content_type: str,
) -> str:
    """
    Upload de bytes para Supabase Storage.

    Retorna o path salvo. Em caso de erro, levanta HTTPException 500
    com body {"error": "..."} (consistente com o padrao de erro da API).

    V1: sem upsert — assume path unico por rodada (garantido pela
    convencao <rodada_id>/... e indice idx quando houver colisao).
    """
    try:
        supabase.storage.from_(bucket).upload(
            path=path,
            file=file_content,
            file_options={"content-type": content_type},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"falha no upload para storage ({bucket}/{path}): {e}"},
        )
    return path
