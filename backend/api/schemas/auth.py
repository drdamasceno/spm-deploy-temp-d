from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserInfo(BaseModel):
    id: UUID
    email: EmailStr


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserInfo


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str


class MeResponse(BaseModel):
    id: UUID
    email: EmailStr
    nome: Optional[str] = None
    role: Optional[str] = None
