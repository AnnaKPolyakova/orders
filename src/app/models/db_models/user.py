from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.db_models.base import BaseId


class User(SQLAlchemyBaseUserTable[int], BaseId):
    __tablename__ = "user"
    name: Mapped[str] = mapped_column(nullable=True)
    phone_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=True
    )
    revoked_tokens = relationship("RevokedToken", back_populates="user")


class RevokedToken(BaseId):
    __tablename__ = "revoked_tokens"

    token = Column(String, unique=True, nullable=False)
    user_id = Column(
        Integer, ForeignKey("user.id"), nullable=False
    )  # <-- важно!
    user = relationship("User", back_populates="revoked_tokens")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
