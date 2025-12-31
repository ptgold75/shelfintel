from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Integer, Float, Text, ForeignKey, func
import uuid

class Base(DeclarativeBase):
    pass

def _uuid():
    return str(uuid.uuid4())

class Dispensary(Base):
    __tablename__ = "dispensary"
    dispensary_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False, default="MD")
    address: Mapped[str] = mapped_column(String(400), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=True)
    zip: Mapped[str] = mapped_column(String(20), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(200), nullable=True)
    menu_url: Mapped[str] = mapped_column(Text, nullable=True)
    menu_provider: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ScrapeRun(Base):
    __tablename__ = "scrape_run"
    scrape_run_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    dispensary_id: Mapped[str] = mapped_column(String, ForeignKey("dispensary.dispensary_id"), nullable=False)
    started_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")
    http_status: Mapped[int] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    records_found: Mapped[int] = mapped_column(Integer, nullable=True)

class RawMenuItem(Base):
    __tablename__ = "raw_menu_item"
    raw_menu_item_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scrape_run_id: Mapped[str] = mapped_column(String, ForeignKey("scrape_run.scrape_run_id"), nullable=False)
    dispensary_id: Mapped[str] = mapped_column(String, ForeignKey("dispensary.dispensary_id"), nullable=False)

    observed_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    raw_name: Mapped[str] = mapped_column(Text, nullable=False)
    raw_category: Mapped[str] = mapped_column(String(120), nullable=True)
    raw_brand: Mapped[str] = mapped_column(String(200), nullable=True)

    raw_price: Mapped[float] = mapped_column(Float, nullable=True)
    raw_discount_price: Mapped[float] = mapped_column(Float, nullable=True)
    raw_discount_text: Mapped[str] = mapped_column(String(250), nullable=True)

    provider_product_id: Mapped[str] = mapped_column(String(200), nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=True)
