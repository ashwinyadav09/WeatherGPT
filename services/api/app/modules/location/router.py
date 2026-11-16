from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.api.app.evidence.models import PlaceModel
from services.api.app.modules.location.resolver import LocationResolver

router = APIRouter(prefix="/places", tags=["places"])
_resolver = LocationResolver()


class ResolveRequest(BaseModel):
    text: str
    language: str = "en"
    hint: str | None = None


@router.get("/search", response_model=list[PlaceModel])
async def search_places(
    q: str = Query(..., description="Place name query"),
    lang: str = Query("en", description="Language code"),
) -> Any:
    return await _resolver.search(query=q, language=lang)


@router.post("/resolve")
async def resolve_places(body: ResolveRequest) -> Any:
    return await _resolver.resolve(text=body.text, language=body.language, hint=body.hint)


@router.get("/{place_id}", response_model=PlaceModel)
async def get_place(place_id: str) -> Any:
    place = await _resolver.get_by_id(place_id)
    if not place:
        raise HTTPException(status_code=404, detail=f"Place {place_id} not found")
    return place
