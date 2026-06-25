import os
import subprocess
import sys


def test_sqlite_checkpointer_resumes_under_strict_msgpack() -> None:
    env = os.environ.copy()
    env["LANGGRAPH_STRICT_MSGPACK"] = "true"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from pathlib import Path
from tempfile import TemporaryDirectory
from noesis.graph.schemas import ConfirmationResult
from noesis.graph.runner import resume_run, start_run
from tests.graph.test_runner_e2e import (
    DynamicFakeLLM,
    make_conn,
    make_deps,
    seed_position_and_entity,
)

with TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    conn = make_conn(tmp_path)
    seed_position_and_entity(conn)
    deps = make_deps(tmp_path, conn, llm=DynamicFakeLLM())
    interrupted = start_run("position-1", deps)
    completed = resume_run(
        interrupted.run_id,
        ConfirmationResult(status="confirmed"),
        deps,
    )
    assert completed.status == "completed"
    conn.close()
""",
        ],
        env=env,
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
