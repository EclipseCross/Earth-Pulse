export type ChangeType = "auto" | "ground" | "forest" | "farming" | "glacier" | "wetland" | "infrastructure";
export interface Observation {
  granule_id: string; product: string; acquisition_start?: string | null; acquisition_end?: string | null;
  size_mb?: number | null; origin: "live" | "demo";
}
export interface SearchResult {
  origin: "live" | "demo"; count: number; products_searched: string[]; observations: Observation[]; notes: string[];
}
export interface ChangeAnalysisResult {
  product: string;
  baseline_granule_id: string;
  comparison_granule_id: string;
  baseline_date: string;
  comparison_date: string;
  layer: string;
  metric: string;
  value: number;
  unit: string;
  interpretation: string;
  caveats: string[];
}
export interface GroundAnalysisResult {
  change_type: string; measurement: string; unit: string; mean: number | null; median: number | null;
  max: number | null; min: number | null; affected_area_km2: number | null; threshold_mm: number;
  coherence_mean: number | null; coherence_threshold: number; valid_fraction: number;
  reference_method: string; reference_value_mm: number | null; granule_ids: string[];
  reference_acquisition_date: string; secondary_acquisition_date: string; track: string; frame: string;
  orbit_direction: string; wavelength_m: number; sign_convention: string; processing_notes: string[];
  limitations: string[]; confidence: string; confidence_reasons: string[]; status: string;
  message: string | null; zones: GeoJSON.FeatureCollection;
}
export interface BackscatterAnalysisResult {
  change_type: string; product: string; measurement: string; unit: string; polarization: string;
  before_granule_id: string; after_granule_id: string; before_date: string | null; after_date: string | null;
  mean_db_change: number | null; affected_area_km2: number | null; threshold_db: number;
  valid_fraction: number; statistical_rule: string; zones: GeoJSON.FeatureCollection;
  status: string; message: string | null; processing_notes: string[]; limitations: string[];
  before_overlay_url: string | null; after_overlay_url: string | null;
}
export interface Place { name: string; lat: number; lon: number }
export interface Watch {
  id: number; lat: number; lon: number; change_type: ChangeType; last_checked: number | null; last_error: string | null;
  baseline_count: number; unread: number;
  new_observations: { granule_id: string; product: string; acquisition_start: string | null; unread: number }[];
}
