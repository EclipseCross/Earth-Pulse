from pydantic import BaseModel, Field

from app.models.observation import Product


class ChangeAnalysisRequest(BaseModel):
    lat: float
    lon: float
    product: Product
    start: str = Field(description="Baseline acquisition date, YYYY-MM-DD")
    end: str = Field(description="Comparison acquisition date, YYYY-MM-DD")


class ChangeAnalysisResult(BaseModel):
    product: Product
    baseline_granule_id: str
    comparison_granule_id: str
    baseline_date: str
    comparison_date: str
    layer: str
    metric: str
    value: float
    unit: str
    interpretation: str
    caveats: list[str]
