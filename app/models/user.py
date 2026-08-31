from typing import Optional, List
from sqlalchemy import BigInteger, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    preferred_fiat: Mapped[str] = mapped_column(String(10), default="usd", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    whale_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    watchlist: Mapped[List["Watchlist"]] = relationship(
        "Watchlist", back_populates="user", cascade="all, delete-orphan"
    )
    price_alerts: Mapped[List["PriceAlert"]] = relationship(
        "PriceAlert", back_populates="user", cascade="all, delete-orphan"
    )
    volume_alerts: Mapped[List["VolumeAlert"]] = relationship(
        "VolumeAlert", back_populates="user", cascade="all, delete-orphan"
    )
    portfolio_holdings: Mapped[List["PortfolioHolding"]] = relationship(
        "PortfolioHolding", back_populates="user", cascade="all, delete-orphan"
    )
    portfolio_transactions: Mapped[List["PortfolioTransaction"]] = relationship(
        "PortfolioTransaction", back_populates="user", cascade="all, delete-orphan"
    )


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    experience_level: Mapped[str] = mapped_column(String(32), default="beginner", nullable=False)
    total_alerts_created: Mapped[int] = mapped_column(default=0, nullable=False)
    tracked_wallet_addresses: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="profile")
