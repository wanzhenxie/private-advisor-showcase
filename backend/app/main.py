from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .database import Base, engine
from .routers import auth, profile, memories, chat, usage

settings = get_settings()

# v0.1 convenience. Replace with Alembic before production.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="私人智囊 Private Advisor API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(memories.router)
app.include_router(chat.router)
app.include_router(usage.router)

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
