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
  frequency_column?: string;
  amplitude_column?: string;
  spectrum_background_path?: string;
};

export type PeriodSpacingSequence = {
  delta_p: number;
  delta_p_start: number;
  delta_p_mid: number;
  delta_p_end: number;
  delta_p_error: number | null;
  p0: number;
  periods: number[];
  amplitudes: number[];
  radial_orders: number[];
  residuals: number[];
  slope: number | null;
  n_modes: number;
  coverage: number;
  confidence_score: number;
  amplitude_score: number;
  amplitude_mean: number;
  amplitude_median: number;
};

export type PeriodRange = {
  period_min: number;
  period_max: number;
  n_points: number;
};

export type AmplitudePeriodCluster = {
  rank: number;
  label: string;
  n_points: number;
  period_min: number;
  period_max: number;
  amplitude_min: number;
  amplitude_max: number;
  amplitude_mean: number;
  amplitude_median: number;
  amplitude_fraction: number;
  period_ranges: PeriodRange[];
};

export type PlotPayload = {
  data: unknown[];
  layout: Record<string, unknown>;
};

export type InputSummary = Record<string, number | string | boolean> & {
  input_period_min?: number;
  input_period_max?: number;
  period_min?: number;
  period_max?: number;
};

export type AnalysisResult = {
  status: "ok";
  input_summary: InputSummary;
  best_sequence: PeriodSpacingSequence | null;
  candidates: PeriodSpacingSequence[];
  amplitude_period_clusters: AmplitudePeriodCluster[];
  plots: {
    echelle: PlotPayload;
    period_spacing: PlotPayload;
    scan: PlotPayload;
    spectrum?: PlotPayload;
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
  snr_threshold: 4,
  frequency_column: undefined,
  amplitude_column: undefined,
  spectrum_background_path: undefined
};
