import logging
import time
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends

from app.models.Carpool import Carpool, Agency
from app.routers.agencyconf import verify_api_key, verify_admin_api_key, verify_permission_for_same_agency_or_admin
# TODO should move this to service
from app.routers.carpool import store_carpool, delete_agency_carpools_older_than
from app.services.agencies import AgencyService
from app.services.importing.ride2go import import_ride2go
from app.utils.container import container
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/agency",
    tags=["agency"]
)


@router.get("/{agency_id}",
            operation_id="getAgencyById",
            summary="Find agency by ID",
            response_model=Agency,
            description="Find agency by ID",
            status_code=status.HTTP_200_OK,
            # TODO next to the status codes are "Links". There is nothing shown now.
            # Either show something there, or hide the Links, or do nothing.
            responses={
                status.HTTP_404_NOT_FOUND: {"description": "Carpool not found"},
                # TODO note that automatic validations against the schema
                # are returned with code 422, also shown in Swagger.
                # maybe 405 is not needed?
                # 405: {"description": "Validation exception"}
            },
            )
async def get_agency(agency_id: str, admin_api_key: str = Depends(verify_api_key)) -> Agency:
    agencies: AgencyService = container['agencies']
    agency = agencies.get_agency(agency_id)
    agency_exists = agency is not None

    if not agency_exists:
        message = f"Agency with id {agency_id} does not exist."
        logger.error(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

    logger.info(f"Get agency {agency_id}.")

    return agency


@router.post("/{agency_id}/sync",
             operation_id="sync",
             summary="Synchronizes all carpool offers",
             response_model=List[Carpool],
             responses={
                 status.HTTP_200_OK: {
                     "description": "Carpool created"},
                 status.HTTP_404_NOT_FOUND: {
                     "description": "Agency does not exist"},
                 status.HTTP_500_INTERNAL_SERVER_ERROR: {
                     "description": "Import error"}
             })
async def sync(agency_id: str, requesting_agency_id: str = Depends(verify_api_key)) -> List[Carpool]:
    await verify_permission_for_same_agency_or_admin(agency_id, requesting_agency_id)

    if agency_id == "ride2go":
        import_function = import_ride2go
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agency does not exist or does not support sync.")

    try:
        carpools = import_function()
        synced_files_older_than = time.time()
        result = [await store_carpool(cp) for cp in carpools]
        await delete_agency_carpools_older_than(agency_id, synced_files_older_than)
        return result
    except BaseException as e:
        logger.exception("Error on sync for agency %s", agency_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Something went wrong during import.")
