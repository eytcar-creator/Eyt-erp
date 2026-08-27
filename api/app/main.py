from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import os

app = FastAPI(title="E.Y.T ERP API", version="1.0.0")

DATABASE_URL = os.getenv("DATABASE_URL", "")
engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)) if DATABASE_URL else None

@app.get("/api/v1/health")
async def health():
    if engine is None:
        return {"status": "ok", "database": "not_configured"}
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
