from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Depends
from sqlalchemy import text
from backend.db.database import engine, AsyncSession, get_db
from backend.modules.vk import router as vk_router
from backend.modules.llm import router as llm_router
from backend.modules.profiles import router as profiles_router
from backend.modules.condition import router as condition_router
from backend.modules.dzen import router as dzen_router
from backend.modules.sheet_parser import router as sheet_parser_router
from backend.modules.report import router as report_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI( title="Безумный MAX",
               description="Платформа для аналитики",
               version="1.0.0",
               lifespan=lifespan 
             )

app.include_router(vk_router)
app.include_router(llm_router)
app.include_router(profiles_router)
app.include_router(condition_router)
app.include_router(dzen_router)
app.include_router(sheet_parser_router)
app.include_router(report_router)

@app.get("/")
async def root():
    return {"message": "Backend is running"}

@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return { "status": "ok", "db_response": result.scalar() }


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
