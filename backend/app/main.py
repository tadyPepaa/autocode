from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import select

from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.learning import router as learning_router
from app.api.projects import router as projects_router
from app.api.research import router as research_router
from app.api.users import router as users_router
from app.api.settings import router as settings_router
from app.api.social import router as social_router
from app.api.ws import router as ws_router
from app.auth import hash_password
from app.database import engine, init_db
from app.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlmodel import Session

    init_db()
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=hash_password("admin"),
                role="admin",
            )
            session.add(admin)
            session.commit()
    yield


app = FastAPI(title="AutoCode", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(research_router, prefix="/api")
app.include_router(learning_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(social_router, prefix="/api")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve frontend static files
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve frontend SPA — all non-API routes return index.html."""
        file_path = _frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dist / "index.html"))
