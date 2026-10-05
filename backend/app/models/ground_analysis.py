from pydantic import BaseModel, Field


class GroundAnalysisRequest(BaseModel):
    lat: float | None = None
    lon: float | None = None
    bbox: tuple[float, float, float, float] | None = None
    change_type: str = Field(default="ground")
    granule_ids: list[str] | None = None


class GroundAnalysisResponse(BaseModel):
    analysis_id: str
    result: dict
