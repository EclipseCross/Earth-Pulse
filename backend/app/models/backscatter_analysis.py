from pydantic import BaseModel, Field

from app.models.observation import Product


class BackscatterAnalysisRequest(BaseModel):
    lat: float | None = None
    lon: float | None = None
    bbox: tuple[float, float, float, float] | None = None
    product: Product = Product.GCOV
    before_granule_id: str | None = None
    after_granule_id: str | None = None
    polarization: str | None = Field(default=None, pattern="^(HH|HV|VH|VV|hh|hv|vh|vv)$")
