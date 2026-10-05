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
export interface Place { name: string; lat: number; lon: number }
export interface Watch {
  id: number; lat: number; lon: number; change_type: ChangeType; last_checked: number | null; last_error: string | null;
  baseline_count: number; unread: number;
  new_observations: { granule_id: string; product: string; acquisition_start: string | null; unread: number }[];
}
