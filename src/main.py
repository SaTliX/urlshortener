from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram
from pydantic import BaseModel
import hashlib
import time

app = FastAPI(title="URLShortener", version="1.0.0")

# In-memory store (suffit pour le projet)
url_store: dict[str, str] = {}

# Métriques métier
urls_created = Counter(
    "urlshortener_urls_created_total",
    "Nombre total d'URLs raccourcies créées",
)
redirects_total = Counter(
    "urlshortener_redirects_total",
    "Nombre total de redirections effectuées",
    ["status"],
)
shorten_duration = Histogram(
    "urlshortener_shorten_duration_seconds",
    "Durée de création d'une URL courte",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1],
)

# Instrumentation HTTP automatique → expose GET /metrics
Instrumentator().instrument(app).expose(app)


class ShortenRequest(BaseModel):
    url: str


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


@app.get("/health")
def health():
    return {"status": "ok", "urls_stored": len(url_store)}


@app.post("/shorten", response_model=ShortenResponse)
def shorten(req: ShortenRequest):
    start = time.time()
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    code = hashlib.md5(req.url.encode()).hexdigest()[:6]
    url_store[code] = req.url
    urls_created.inc()
    shorten_duration.observe(time.time() - start)

    return ShortenResponse(
        short_code=code,
        short_url=f"http://localhost:8000/r/{code}",
        original_url=req.url,
    )


@app.get("/r/{code}")
def redirect(code: str):
    if code not in url_store:
        redirects_total.labels(status="not_found").inc()
        raise HTTPException(status_code=404, detail="Short URL not found")
    redirects_total.labels(status="ok").inc()
    return RedirectResponse(url=url_store[code], status_code=302)


@app.get("/urls")
def list_urls():
    return {"count": len(url_store), "urls": url_store}
