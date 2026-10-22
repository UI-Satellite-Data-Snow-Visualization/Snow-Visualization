from fastapi import FastAPI
from server.routes import watersheds

app = FastAPI(title="Snow Visualization API")
app.include_router(watersheds.router, prefix="/watersheds")


@app.get("/health")
def health():
    return {"status": "ok"}
