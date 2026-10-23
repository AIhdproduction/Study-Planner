from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path() -> Path:
    path = Path(".test-temp") / uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    return path
