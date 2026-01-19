from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models.task import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./localclip.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """初始化数据库表"""
    print("[数据库] 初始化数据库表...")
    Base.metadata.create_all(bind=engine)
    print("[数据库] 数据库表初始化完成")

def get_db() -> Session:
    """获取数据库会话（用于 FastAPI Depends）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
