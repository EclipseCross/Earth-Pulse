from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    earthpulse_mode: str = "live"  # live | demo
    cors_origins: str = "http://localhost:3000"
    ai_api_key: str = ""
    database_url: str = ""
    earthdata_username: str = ""
    earthdata_password: str = ""
    earthdata_token: str = ""
    nisar_shortname_gunw: str = ""
    nisar_shortname_gslc: str = ""
    nisar_shortname_gcov: str = ""
    nisar_shortname_goff: str = ""
    nisar_shortname_sme2: str = ""
    watch_interval_minutes: int = 180  # 0 disables the background watcher
    search_cache_seconds: int = 600
    watch_db_path: str = "data/watches.db"
    geocoder_url: str = "https://nominatim.openstreetmap.org/search"
    coherence_threshold: float = 0.5  # standard coherence screening: reject decorrelated pixels below 0.5
    min_valid_fraction: float = 0.1  # require at least 10% valid pixels to avoid sparse/noisy summaries
    displacement_threshold_mm: float = 10.0  # configurable screening threshold, not an engineering damage limit
    min_zone_area_km2: float = 0.01  # suppress isolated pixels smaller than 0.01 km2
    reference_method: str = "median_high_coherence"  # robust relative reference for an AOI without a surveyed point
    require_main_component: bool = True
    max_processing_pixels: int = 2_000_000  # protect the API from accidentally loading a whole large granule
    backscatter_threshold_db: float = 3.0  # common first-pass SAR screening threshold; configurable, not a confirmed-event limit
    backscatter_z_threshold: float | None = None  # optional robust statistical screen; disabled by default until AOI calibration exists
    backscatter_multilook_factor: int = 1  # preserve native resolution by default; block averaging reduces speckle when explicitly enabled

    def short_name_overrides(self) -> dict[str, str]:
        return {k: v for k, v in {
            "GUNW": self.nisar_shortname_gunw,
            "GSLC": self.nisar_shortname_gslc,
            "GCOV": self.nisar_shortname_gcov,
            "GOFF": self.nisar_shortname_goff,
            "SME2": self.nisar_shortname_sme2,
        }.items() if v}


settings = Settings()
