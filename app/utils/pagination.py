from dataclasses import dataclass

from fastapi import Query


@dataclass
class PageParams:
    skip: int
    limit: int


def pagination_params(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> PageParams:
    return PageParams(skip=skip, limit=limit)
