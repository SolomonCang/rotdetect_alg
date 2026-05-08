export type SearchConfig = {
  period_min: number;
  period_max: number;
  delta_p_min: number;
  delta_p_max: number;
  delta_p_grid: number;
  min_modes: number;
  top_k_candidates: number;
  tolerance_fraction: number;
  max_peaks: number;
  peak_threshold_factor: number;
  snr_threshold: number;
};

export type PeriodSpacingSequence = {
  delta_p: number;
  delta_p_error: number | null;
  p0: number;
  periods: number[];
  radial_orders: number[];
  residuals: number[];
  slope: number | null;
  n_modes: number;
  coverage: number;
  confidence_score: number;
};

export type PlotPayload = {
  data: unknown[];
  layout: Record<string, unknown>;
};

export type AnalysisResult = {
  status: "ok";
  input_summary: Record<string, number | string | boolean>;
  best_sequence: PeriodSpacingSequence | null;
  candidates: PeriodSpacingSequence[];
  plots: {
    echelle: PlotPayload;
    period_spacing: PlotPayload;
    scan: PlotPayload;
  };
  warnings: string[];
};

export const defaultConfig: SearchConfig = {
  period_min: 0.3,
  period_max: 3.0,
  delta_p_min: 0.005,
  delta_p_max: 0.08,
  delta_p_grid: 0.0001,
  min_modes: 5,
  top_k_candidates: 20,
  tolerance_fraction: 0.1,
  max_peaks: 200,
  peak_threshold_factor: 4,
  snr_threshold: 4
};
