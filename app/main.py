from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as query_router
from app.api.auth_routes import router as auth_router
from app.db import initialize_database


app = FastAPI(title="Church Database Management System", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(query_router)


@app.on_event("startup")
def startup_event() -> None:
    initialize_database()


base_dir = Path(__file__).resolve().parent.parent
web_dir = base_dir / "web"

app.mount("/static", StaticFiles(directory=web_dir), name="static")


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(web_dir / "index.html")
