from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from reexplain_api.config import Settings, get_settings


async def require_service_key(
    settings: Annotated[Settings, Depends(get_settings)],
    supplied_key: Annotated[str | None, Header(alias="X-ReExplain-Service-Key")] = None,
) -> None:
    configured_key = (
        settings.reexplain_api_service_key.get_secret_value()
        if settings.reexplain_api_service_key
        else ""
    )

    if not configured_key or not supplied_key or not compare_digest(supplied_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication required.",
        )