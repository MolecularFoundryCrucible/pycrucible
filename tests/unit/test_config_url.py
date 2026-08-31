import warnings

import pytest

from crucible.client import CrucibleClient
from crucible.config.config import Config


def test_config_defaults_to_v3_api(monkeypatch):
    monkeypatch.setattr(Config, "_load", lambda self: None)

    config = Config()

    assert config.api_url == "https://crucible.lbl.gov/api/v3"


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_client_warns_for_legacy_api_path(version):
    with pytest.warns(DeprecationWarning, match=f"API {version}"):
        CrucibleClient(
            api_url=f"https://crucible.lbl.gov/api/{version}",
            api_key="test",
        )


def test_client_accepts_custom_url_without_legacy_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        CrucibleClient(
            api_url="https://crucible.lbl.gov/testapi-staging",
            api_key="test",
        )

    assert not caught
