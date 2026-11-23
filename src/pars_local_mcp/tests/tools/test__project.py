"""Check shared project ID validation without database access."""

import pytest

from pars_local_mcp.mcp.errors import PublicError
from pars_local_mcp.mcp.tools._project import _require_project_id


@pytest.mark.parametrize("value", ["", " ", "\t"])
def test_blank_project_id_is_refused(value):
    with pytest.raises(PublicError, match="project_id is required"):
        _require_project_id(value)


def test_valid_project_id_is_preserved():
    assert _require_project_id("proj_001") == "proj_001"
