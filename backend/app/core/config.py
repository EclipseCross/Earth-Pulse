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

    def short_name_overrides(self) -> dict[str, str]:
        return {k: v for k, v in {
            "GUNW": self.nisar_shortname_gunw,
            "GSLC": self.nisar_shortname_gslc,
            "GCOV": self.nisar_shortname_gcov,
            "GOFF": self.nisar_shortname_goff,
            "SME2": self.nisar_shortname_sme2,
        }.items() if v}


settings = Settings()
