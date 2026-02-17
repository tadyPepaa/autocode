from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select

from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.research import router as research_router
from app.api.users import router as users_router
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
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(research_router, prefix="/api")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
