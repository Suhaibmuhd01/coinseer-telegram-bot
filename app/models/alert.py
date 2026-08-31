from sqlalchemy import BigInteger, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class PriceAlert(Base, TimestampMixin):
    __tablename__ = "price_alerts"

    alert_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    coin_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    condition: Mapped[str] = mapped_column(String(10), nullable=False)  # 'above' or 'below'
    fiat: Mapped[str] = mapped_column(String(10), default="usd", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_triggered_at: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="price_alerts")


class VolumeAlert(Base, TimestampMixin):
    __tablename__ = "volume_alerts"

    alert_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    coin_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold_multiplier: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    fiat: Mapped[str] = mapped_column(String(10), default="usd", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="volume_alerts")
