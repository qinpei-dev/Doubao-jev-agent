"""Keep the README showcase backed by the real controlled runner."""

import asyncio

from examples.showcase import run_showcase


def test_showcase_runs_all_three_paths_without_leaking_file_contents():
    output = asyncio.run(run_showcase())
    assert "JEV (mock)  ALLOW " in output
    assert "Result      WAITING FOR APPROVAL" in output
    assert "Result      EXECUTED AFTER APPROVAL" in output
    assert "Policy      DENY" in output
    assert output.count("Executor    NOT CALLED") == 2
    assert "before approval" not in output
    assert "after approval\n" not in output
