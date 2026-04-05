from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass


def init_db():
    """初始化数据库表"""
    from src.db.session import engine
    Base.metadata.create_all(bind=engine)