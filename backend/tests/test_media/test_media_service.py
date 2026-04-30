import pytest
from app.modules.media.service import MediaService

@pytest.mark.asyncio
async def test_media_service_init():
    service = MediaService()
    assert service is not None
    assert service.s3_config["aws_access_key_id"] == "minioadmin"
