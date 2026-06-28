import pytest
from fastapi.testclient import TestClient
from src.main import app, url_store

client = TestClient(app)


def setup_function():
    """Vider le store avant chaque test."""
    url_store.clear()


# ── /health ─────────────────────────────────────────────────────────────────

def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_returns_url_count():
    url_store["abc123"] = "https://example.com"
    resp = client.get("/health")
    assert resp.json()["urls_stored"] == 1


# ── /shorten ─────────────────────────────────────────────────────────────────

def test_shorten_valid_url():
    resp = client.post("/shorten", json={"url": "https://openai.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
    assert data["original_url"] == "https://openai.com"


def test_shorten_same_url_returns_same_code():
    r1 = client.post("/shorten", json={"url": "https://same.com"})
    r2 = client.post("/shorten", json={"url": "https://same.com"})
    assert r1.json()["short_code"] == r2.json()["short_code"]


def test_shorten_different_urls_different_codes():
    r1 = client.post("/shorten", json={"url": "https://foo.com"})
    r2 = client.post("/shorten", json={"url": "https://bar.com"})
    assert r1.json()["short_code"] != r2.json()["short_code"]


def test_shorten_invalid_url_returns_400():
    resp = client.post("/shorten", json={"url": "not-a-url"})
    assert resp.status_code == 400


def test_shorten_url_stored():
    resp = client.post("/shorten", json={"url": "https://stored.com"})
    code = resp.json()["short_code"]
    assert code in url_store
    assert url_store[code] == "https://stored.com"


# ── /r/{code} ────────────────────────────────────────────────────────────────

def test_redirect_known_code():
    client.post("/shorten", json={"url": "https://redirect-target.com"})
    code = list(url_store.keys())[0]
    resp = client.get(f"/r/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://redirect-target.com"


def test_redirect_unknown_code_returns_404():
    resp = client.get("/r/zzzzzz")
    assert resp.status_code == 404


# ── /urls ────────────────────────────────────────────────────────────────────

def test_list_urls_empty():
    resp = client.get("/urls")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_list_urls_after_shorten():
    client.post("/shorten", json={"url": "https://list-test.com"})
    resp = client.get("/urls")
    assert resp.json()["count"] == 1
