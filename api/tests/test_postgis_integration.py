import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("EOC_RUN_INTEGRATION") != "1",
    reason="requires an explicit PostgreSQL/PostGIS test database",
)
async def test_postgis_schema_and_spatial_index() -> None:
    engine = create_async_engine(os.environ["EOC_DATABASE_URL"])
    try:
        async with engine.connect() as connection:
            postgis = await connection.scalar(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis')")
            )
            spatial_index = await connection.scalar(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_indexes "
                    "WHERE indexname='ix_canonical_records_geom' "
                    "AND indexdef ILIKE '%USING gist%')"
                )
            )
            distance = await connection.scalar(
                text(
                    "SELECT ST_Distance("
                    "ST_SetSRID(ST_Point(-80.13, 25.79), 4326)::geography,"
                    "ST_SetSRID(ST_Point(-80.14, 25.79), 4326)::geography)"
                )
            )
        assert postgis is True
        assert spatial_index is True
        assert distance is not None
        assert distance > 0
    finally:
        await engine.dispose()
