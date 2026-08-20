from sqlalchemy import Row, Select
from sqlalchemy.ext.asyncio import AsyncSession


async def fetch_page_with_total(session: AsyncSession, page_query: Select, count_query: Select) -> tuple[list[Row], int]:
    rows = (await session.execute(page_query)).all()
    total = rows[0].total if rows else (await session.execute(count_query)).scalar_one()

    return rows, total
