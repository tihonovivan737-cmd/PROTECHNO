from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Depends
from sqlalchemy import text

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI( title="Безумный MAX",
               description="Платформа для аналитики",
               version="1.0.0",
               lifespan=lifespan 
             )


@app.get("/")
async def root():
    return {"message": "Backend is running"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
