from __future__ import annotations

from fastapi import APIRouter, Depends

from app.application.use_cases.catalog import (
    AddItem,
    CatalogManifestation,
    CreateWork,
    UpdateManifestation,
    UpdateWork,
)
from app.interface.api import deps
from app.interface.api.params import IdPath
from app.interface.api.schemas import (
    AddItemRequest,
    CatalogWorkResponse,
    CreateManifestationRequest,
    CreateWorkRequest,
    ItemResponse,
    ManifestationResponse,
    UpdateManifestationRequest,
    UpdateWorkRequest,
    WorkResponse,
)

router = APIRouter(tags=["catalog"])


@router.get("/catalog", response_model=list[CatalogWorkResponse])
def get_catalog(query=Depends(deps.get_query_service)) -> list:
    return list(query.catalog())


@router.post("/works", status_code=201, response_model=WorkResponse)
def create_work(
    body: CreateWorkRequest, uc: CreateWork = Depends(deps.get_create_work)
) -> WorkResponse:
    return uc.execute(body.title, body.author)


@router.post(
    "/manifestations", status_code=201, response_model=ManifestationResponse
)
def catalog_manifestation(
    body: CreateManifestationRequest,
    uc: CatalogManifestation = Depends(deps.get_catalog_manifestation),
) -> ManifestationResponse:
    return uc.execute(
        work_id=body.work_id,
        title=body.title,
        material_type=body.material_type,
        isbn=body.isbn,
        publisher=body.publisher,
    )


@router.post(
    "/manifestations/{manifestation_id}/items",
    status_code=201,
    response_model=ItemResponse,
)
def add_item(
    manifestation_id: IdPath,
    body: AddItemRequest,
    uc: AddItem = Depends(deps.get_add_item),
) -> ItemResponse:
    return uc.execute(manifestation_id, body.barcode)


@router.put("/works/{work_id}", response_model=WorkResponse)
def update_work(
    work_id: IdPath,
    body: UpdateWorkRequest,
    uc: UpdateWork = Depends(deps.get_update_work),
) -> WorkResponse:
    return uc.execute(work_id, body.title, body.author)


@router.put(
    "/manifestations/{manifestation_id}", response_model=ManifestationResponse
)
def update_manifestation(
    manifestation_id: IdPath,
    body: UpdateManifestationRequest,
    uc: UpdateManifestation = Depends(deps.get_update_manifestation),
) -> ManifestationResponse:
    return uc.execute(
        manifestation_id=manifestation_id,
        title=body.title,
        material_type=body.material_type,
        isbn=body.isbn,
        publisher=body.publisher,
    )
