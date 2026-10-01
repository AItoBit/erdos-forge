import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--lean-project",
        default=None,
        help="Lake project with built dependencies; enables the `lean` integration tests "
        "(same as setting ERDOS_FORGE_LEAN_PROJECT).",
    )


def pytest_configure(config: pytest.Config) -> None:
    project = config.getoption("--lean-project")
    if project:
        os.environ["ERDOS_FORGE_LEAN_PROJECT"] = project
