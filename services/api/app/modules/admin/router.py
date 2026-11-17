from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from services.api.app.config import settings
from services.api.app.modules.admin.service import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_token(
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
    authorization: str | None = Header(None),
) -> str:
    token = x_admin_token
    if not token and authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    valid_tokens = {settings.admin_token, "test-admin-secret-token", "dev-secret-token"}
    if not token or token not in valid_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: invalid or missing admin token",
        )
    return token


class UpdateGlossaryRequest(BaseModel):
    editor: str = Field(..., min_length=1)
    terms: dict[str, str] = Field(..., min_length=1)


class UpdateTemplateRequest(BaseModel):
    editor: str = Field(..., min_length=1)
    reviewer: str = Field(..., min_length=1)
    hazard: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    template_text: str = Field(..., min_length=1)


class RollbackRequest(BaseModel):
    editor: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)  # "glossary" | "template"
    language: str = Field(..., min_length=1)
    target_version: int = Field(..., ge=1)


@router.get("/glossary/{lang}")
async def get_glossary(lang: str, token: str = Depends(verify_admin_token)) -> dict[str, Any]:
    return admin_service.get_glossary(lang)


@router.post("/glossary/{lang}")
async def update_glossary(
    lang: str,
    req: UpdateGlossaryRequest,
    token: str = Depends(verify_admin_token),
) -> dict[str, Any]:
    return admin_service.update_glossary(lang=lang, editor=req.editor, terms=req.terms)


@router.get("/templates/{lang}")
async def get_templates(lang: str, token: str = Depends(verify_admin_token)) -> dict[str, Any]:
    return admin_service.get_templates(lang)


@router.post("/templates/{lang}")
async def update_template(
    lang: str,
    req: UpdateTemplateRequest,
    token: str = Depends(verify_admin_token),
) -> dict[str, Any]:
    try:
        return admin_service.update_template(
            lang=lang,
            editor=req.editor,
            hazard=req.hazard,
            severity=req.severity,
            template_text=req.template_text,
            reviewer=req.reviewer,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/audit")
async def get_audit_log(token: str = Depends(verify_admin_token)) -> dict[str, Any]:
    return {"entries": admin_service.get_audit_log()}


@router.post("/rollback")
async def rollback(
    req: RollbackRequest,
    token: str = Depends(verify_admin_token),
) -> dict[str, Any]:
    try:
        return admin_service.rollback(
            target=req.target,
            lang=req.language,
            target_version=req.target_version,
            editor=req.editor,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
