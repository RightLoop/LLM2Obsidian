"""Search routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from obsidian_agent.api.deps import get_api_container
from obsidian_agent.domain.schemas import SearchResponse

router = APIRouter(tags=["search"])
ContainerDep = Annotated[object, Depends(get_api_container)]


@router.get("/search")
async def search(container: ContainerDep, q: str = Query(..., min_length=1)) -> SearchResponse:
    results = await container.retrieval_service.hybrid_search(q, top_k=5)
    return SearchResponse(query=q, results=results)


@router.get("/notes/related")
async def related(path: str, container: ContainerDep) -> dict[str, object]:
    results = await container.link_workflow.run(path, top_k=5)
    return {"path": path, "results": [item.model_dump(mode="json") for item in results]}
