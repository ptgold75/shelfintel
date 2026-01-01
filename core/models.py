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
# --- Availability tracking tables ---

class MenuItemState(Base):
    __tablename__ = "menu_item_state"

    menu_item_state_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)

    dispensary_id: Mapped[str] = mapped_column(String, ForeignKey("dispensary.dispensary_id"), nullable=False)

    # This is the stable identifier for a product coming from the provider.
    # We can start with provider_product_id from RawMenuItem.
    provider_product_id: Mapped[str] = mapped_column(String(200), nullable=False)

    raw_name: Mapped[str] = mapped_column(Text, nullable=True)
    raw_category: Mapped[str] = mapped_column(String(120), nullable=True)
    raw_brand: Mapped[str] = mapped_column(String(200), nullable=True)

    first_seen_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    currently_listed: Mapped[bool] = mapped_column(Integer, nullable=False, default=1)  # 1/0 works fine in PG too
    last_missing_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MenuItemEvent(Base):
    __tablename__ = "menu_item_event"

    menu_item_event_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)

    dispensary_id: Mapped[str] = mapped_column(String, ForeignKey("dispensary.dispensary_id"), nullable=False)
    scrape_run_id: Mapped[str] = mapped_column(String, ForeignKey("scrape_run.scrape_run_id"), nullable=False)

    provider_product_id: Mapped[str] = mapped_column(String(200), nullable=False)

    # "appeared" or "disappeared"
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)

    event_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    raw_name: Mapped[str] = mapped_column(Text, nullable=True)
    raw_category: Mapped[str] = mapped_column(String(120), nullable=True)
    raw_brand: Mapped[str] = mapped_column(String(200), nullable=True)
