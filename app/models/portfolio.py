from typing import Optional
from sqlalchemy import BigInteger, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class PortfolioHolding(Base, TimestampMixin):
    __tablename__ = "portfolio_holdings"
    __table_args__ = (
        UniqueConstraint("user_id", "coin_id", name="uq_user_coin_holding"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    coin_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    average_buy_price: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="portfolio_holdings")


class PortfolioTransaction(Base, TimestampMixin):
    __tablename__ = "portfolio_transactions"

    transaction_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    coin_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'buy' or 'sell'
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    fiat: Mapped[str] = mapped_column(String(10), default="usd", nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="portfolio_transactions")
