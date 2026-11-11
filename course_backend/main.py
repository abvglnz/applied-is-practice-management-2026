from contextlib import asynccontextmanager

from fastapi import FastAPI

from course_backend.database.db import init_db
from course_backend.routers.placements import router as placements_router
from course_backend.seed import seed_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_database()
    yield


app = FastAPI(
    title="Кәсіби практиканы басқару API",
    description="Студенттердің практикаға бөлінуін басқаруға арналған оқу REST API.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(placements_router)


@app.get("/health", tags=["Қызмет күйі"])
def health():
    return {"status": "ok", "service": "praktika-api"}
