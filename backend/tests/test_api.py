import os
os.environ["DATABASE_URL"] = "sqlite:///./test_researchhub.db"
os.environ["SECRET_KEY"] = "test-secret"
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_register_login_and_project():
    email = "test_unique_researcher@example.com"
    r = client.post("/api/auth/register", json={
        "name": "Test Researcher",
        "email": email,
        "password": "StrongPass123!",
        "role": "researcher",
        "research_interest": "AI"
    })
    assert r.status_code in (200, 409)
    token = r.json().get("token") if r.status_code == 200 else None
    if not token:
        r = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
        assert r.status_code == 200
        token = r.json()["token"]
    headers={"Authorization": f"Bearer {token}"}
    r = client.post("/api/projects", headers=headers, json={"title":"Test Research Project","description":"Reproducible experiment"})
    assert r.status_code == 200
    project_id = r.json()["id"]
    r = client.get(f"/api/projects/{project_id}", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["milestones"]) == 3

def test_integrity_check():
    # Uses a freshly registered account to avoid assumptions about test ordering.
    email = "integrity_unique@example.com"
    r = client.post("/api/auth/register", json={"name":"Integrity","email":email,"password":"StrongPass123!","role":"researcher"})
    if r.status_code == 409:
        r = client.post("/api/auth/login", json={"email":email,"password":"StrongPass123!"})
    token = r.json()["token"]
    r = client.post("/api/research/integrity-check", headers={"Authorization":f"Bearer {token}"}, json={"prompt":"ransomware classification"})
    assert r.status_code == 200
    assert len(r.json()["checks"]) >= 4
