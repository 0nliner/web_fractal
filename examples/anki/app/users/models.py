from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from web_fractal.db import Base, Dated


class User(Base, Dated):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(32), default="student")
    is_active: Mapped[bool] = mapped_column(default=True)
