from enum import Enum
from pydantic import BaseModel


class Product(str, Enum):
    GUNW = "GUNW"
    GSLC = "GSLC"
    GCOV = "GCOV"
    GOFF = "GOFF"
    SME2 = "SME2"


class DataOrigin(str, Enum):
    LIVE = "live"   # returned by NASA CMR right now
    DEMO = "demo"   # preprocessed real NISAR metadata/products stored locally


class Observation(BaseModel):
    granule_id: str
    product: Product
    acquisition_start: str | None = None
    acquisition_end: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    size_mb: float | None = None
    download_url: str | None = None
    origin: DataOrigin


class SearchResult(BaseModel):
    origin: DataOrigin
    bbox: tuple[float, float, float, float]
    products_searched: list[Product]
    count: int
    observations: list[Observation]
    notes: list[str] = []
