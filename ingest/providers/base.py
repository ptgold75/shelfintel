# ingest/providers/base.py
"""Base provider class for menu scraping."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator, Optional, Any

@dataclass
class MenuItem:
    """Represents a single menu item from a dispensary."""
    provider_product_id: str
    raw_name: str
    raw_brand: Optional[str] = None
    raw_category: Optional[str] = None
    raw_price: Optional[float] = None
    raw_discount_price: Optional[float] = None
    raw_discount_text: Optional[str] = None
    raw_description: Optional[str] = None
    raw_json: dict = field(default_factory=dict)

class BaseProvider(ABC):
    """Abstract base class for dispensary menu providers."""
    
    name: str = "base"
    
    def __init__(self, dispensary_id: str):
        self.dispensary_id = dispensary_id
    
    @abstractmethod
    def scrape(self) -> Generator[MenuItem, None, None]:
        """Scrape menu items from the dispensary."""
        pass
