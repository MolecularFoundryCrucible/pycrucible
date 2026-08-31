from crucible.cli.status import _readiness_fields


def test_readiness_fields_parses_nested_provenance():
    health = {
        "status": "ok",
        "build": {
            "api_version": "3.0.0",
            "git_commit": "a" * 40,
            "branch": "staging",
        },
        "database": {
            "status": "ok",
            "latency_ms": 2.5,
            "schema_revisions": ["d6e1f8a2c4b7"],
        },
    }

    assert _readiness_fields(health) == ("3.0.0", "ok", 2.5, True)


def test_readiness_fields_keeps_legacy_flat_compatibility():
    health = {"status": "ok", "db": "ok", "db_ms": 3.0, "version": "2.0.0"}

    assert _readiness_fields(health) == ("2.0.0", "ok", 3.0, True)


def test_readiness_fields_reports_unknown_contract():
    assert _readiness_fields({"status": "ok"}) == (None, None, None, False)
