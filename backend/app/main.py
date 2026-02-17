from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select

from app.api.auth import router as auth_router
from app.api.deps import get_current_user
from app.api.users import router as users_router
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

# Stub router for agents — will be replaced by full CRUD in Task 5
agents_router = APIRouter(prefix="/agents", tags=["agents"])


@agents_router.get("")
async def list_agents(user: User = Depends(get_current_user)):
    return []


app.include_router(agents_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
