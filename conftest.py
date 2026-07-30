import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def tenant(client):
    resp = client.post("/v1/tenants", json={"name": f"Test Bank {uuid.uuid4()}", "industry": "bank"})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture()
def approver(client, tenant):
    resp = client.post(
        "/v1/users",
        headers={"X-Tenant-Id": tenant},
        json={"email": f"officer-{uuid.uuid4()}@test.local", "full_name": "Test Officer"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]
