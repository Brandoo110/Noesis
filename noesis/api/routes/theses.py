from fastapi import APIRouter, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import ConfirmThesisRequest, RunResponse
from noesis.graph.errors import ResearchNodeError
from noesis.graph.runner import resume_run
from noesis.graph.state import GraphDeps

router = APIRouter(prefix="/theses", tags=["theses"])


@router.post("/{thesis_id}/confirm", response_model=RunResponse)
def confirm_thesis(
    thesis_id: str,
    request: ConfirmThesisRequest,
    deps: GraphDeps = Depends(get_graph_deps),
) -> RunResponse:
    run_id = _run_id_from_thesis_id(thesis_id)
    if deps.repos.runs.get(run_id) is None:
        raise ResearchNodeError("run not found", reason="run_not_found")
    handle = resume_run(run_id, request.to_confirmation(), deps)
    return RunResponse(
        run_id=handle.run_id,
        status=handle.status,
        thesis_id=handle.thesis_id,
    )


def _run_id_from_thesis_id(thesis_id: str) -> str:
    if not thesis_id.startswith("thesis-run-"):
        raise ResearchNodeError("invalid thesis id", reason="invalid_thesis_id")
    return thesis_id.removeprefix("thesis-")
