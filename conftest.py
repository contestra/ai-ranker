
import os
import importlib
import types
import pytest
from fastapi.testclient import TestClient

# Point the app to a local SQLite file for tests BEFORE importing the module.
os.environ.setdefault("DB_URL", "sqlite:///./test_prompter_pytest.db")
os.environ.setdefault("CREATE_ALL_ON_STARTUP", "true")

@pytest.fixture(scope="session")
def app_module():
    # Import after env is set so the router binds to the test DB
    mod = importlib.import_module("prompter_router_min")
    return mod

@pytest.fixture(scope="session")
def app(app_module):
    return app_module.app

@pytest.fixture()
def client(app):
    return TestClient(app)

@pytest.fixture()
def patch_version_service(app_module, monkeypatch):
    """Patch ensure_version_service to avoid live provider probes during tests."""
    from datetime import datetime
    def _stub(db, **kwargs):
        return {
            "version_id": "00000000-0000-0000-0000-000000000001",
            "provider_version_key": "stub-pvk",
            "captured_at": datetime.utcnow(),
        }
    monkeypatch.setattr(app_module, "ensure_version_service", _stub)
    return _stub
