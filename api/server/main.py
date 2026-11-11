from fastapi import FastAPI
from server.routes import pca, watersheds
from snow import products

app = FastAPI(title="Snow Visualization API")
app.include_router(watersheds.router, prefix="/watersheds")
app.include_router(pca.router, prefix="/pca")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/products", tags=["products"])
def list_products():
    """Satellite products the API can read (MODIS and VIIRS). Use `key` as `product` elsewhere."""
    return [{**p.summary(), "default": p is products.DEFAULT} for p in products.ALL]
