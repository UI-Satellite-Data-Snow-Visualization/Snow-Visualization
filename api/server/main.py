from fastapi import FastAPI
from server.routes import pca, watersheds

app = FastAPI(title="Snow Visualization API")
app.include_router(watersheds.router, prefix="/watersheds")
app.include_router(pca.router, prefix="/pca")


@app.get("/health")
def health():
    return {"status": "ok"}
