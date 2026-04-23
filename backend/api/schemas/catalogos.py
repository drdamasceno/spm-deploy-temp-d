from uuid import UUID
from pydantic import BaseModel


class EmpresaOut(BaseModel):
    id: UUID
    codigo: str
    razao_social: str
    cnpj: str | None = None
    ativa: bool
    regime_tributario: str | None = None  # LUCRO_REAL / LUCRO_PRESUMIDO / SIMPLES_NACIONAL
    papel: str | None = None  # PRINCIPAL / INTRAGRUPO


class CategoriaOut(BaseModel):
    id: UUID
    nome: str
    descricao: str | None = None


class ProjetoIn(BaseModel):
    codigo: str
    descricao: str | None = None
    empresa_id: UUID


class ProjetoOut(ProjetoIn):
    id: UUID
    ativo: bool
