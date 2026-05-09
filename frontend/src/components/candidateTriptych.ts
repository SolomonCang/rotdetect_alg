import type { AnalysisResult, PeriodSpacingSequence, PlotPayload } from "../types";

type SpectrumPoint = {
  period: number;
  amplitude: number;
};

type SpectrumSeries = {
  points: SpectrumPoint[];
  continuous: boolean;
};

const PANEL_BG = "#ffffff";
const FRAME_COLOR = "#606060";
const BASE_FONT = "Times New Roman, Georgia, serif";

export function buildCandidateTriptychPayload(
  result: AnalysisResult,
  selectedCandidateIndex: number
): PlotPayload {
  const candidate = pickCandidate(result.candidates, selectedCandidateIndex);
  if (!candidate) {
    return {
      data: [],
      layout: {
        title: { text: "Candidate diagnostics", font: { family: BASE_FONT, size: 22 } },
        annotations: [
          {
            text: "No candidate sequence available",
            showarrow: false,
            x: 0.5,
            y: 0.5,
            xref: "paper",
            yref: "paper"
          }
        ],
        paper_bgcolor: PANEL_BG,
        plot_bgcolor: PANEL_BG,
        font: { family: BASE_FONT, size: 16, color: "#202020" }
      }
    };
  }

  const peakPoints = parsePeakPoints(result);
  const spectrumSeries = parseFullSpectrumSeries(result);
  const spectrumPoints = spectrumSeries?.points ?? peakPoints;
  const sequencePeriodRange = getCandidatePeriodRange(candidate);

  if (spectrumPoints.length === 0 || peakPoints.length === 0) {
    return {
      data: [],
      layout: {
        title: { text: "Candidate diagnostics", font: { family: BASE_FONT, size: 22 } },
        annotations: [
          {
            text: "No spectrum points available",
            showarrow: false,
            x: 0.5,
            y: 0.5,
            xref: "paper",
            yref: "paper"
          }
        ],
        paper_bgcolor: PANEL_BG,
        plot_bgcolor: PANEL_BG,
        font: { family: BASE_FONT, size: 16, color: "#202020" }
      }
    };
  }

  const panelAData = buildPanelA(
    spectrumPoints,
    peakPoints,
    candidate,
    sequencePeriodRange,
    spectrumSeries?.continuous ?? false
  );
  const panelBData = buildPanelB(candidate, sequencePeriodRange);
  const panelCData = buildPanelC(peakPoints, candidate, sequencePeriodRange);

  return {
    data: [...panelAData, ...panelBData, ...panelCData],
    layout: {
      title: {
        text: `Candidate diagnostics (${selectedCandidateIndex + 1}/${result.candidates.length})`,
        font: { family: BASE_FONT, size: 24 }
      },
      font: { family: BASE_FONT, size: 16, color: "#202020" },
      grid: {
        rows: 3,
        columns: 1,
        pattern: "independent",
        roworder: "top to bottom"
      },
      height: 980,
      margin: { l: 78, r: 26, t: 70, b: 92 },
      legend: {
        orientation: "h",
        yanchor: "top",
        y: -0.08,
        xanchor: "left",
        x: 0,
        font: { family: BASE_FONT, size: 14 }
      },
      paper_bgcolor: PANEL_BG,
      plot_bgcolor: PANEL_BG,
      xaxis: buildAxis("$P\\,(\\mathrm{d})$", sequencePeriodRange),
      yaxis: buildAxis("$A\\,(\\mathrm{ppm})$"),
      xaxis2: buildAxis("$\\left(P_i + P_{i+1}\\right)/2\\,(\\mathrm{d})$", sequencePeriodRange),
      yaxis2: buildAxis("$\\Delta P\\,(\\mathrm{s})$"),
      xaxis3: buildAxis("$P\\,(\\mathrm{d})$", sequencePeriodRange),
      yaxis3: buildAxis("$P - (P_0 + \\Delta P_0 n^{\\prime})\\,(\\mathrm{s})$"),
      annotations: [
        { text: "a", showarrow: false, x: 0.04, y: 0.98, xref: "paper", yref: "paper", font: { family: BASE_FONT, size: 32, color: "#121212" } },
        { text: "b", showarrow: false, x: 0.04, y: 0.64, xref: "paper", yref: "paper", font: { family: BASE_FONT, size: 32, color: "#121212" } },
        { text: "c", showarrow: false, x: 0.04, y: 0.31, xref: "paper", yref: "paper", font: { family: BASE_FONT, size: 32, color: "#121212" } }
      ]
    }
  };
}

function buildAxis(title: string, range?: [number, number]): Record<string, unknown> {
  return {
    title: { text: title },
    ...(range ? { range } : {}),
    showline: true,
    linecolor: FRAME_COLOR,
    linewidth: 1,
    ticks: "outside",
    tickcolor: FRAME_COLOR,
    ticklen: 5,
    tickwidth: 1,
    gridcolor: "rgba(0,0,0,0)",
    zeroline: false,
    automargin: true
  };
}

function pickCandidate(
  candidates: PeriodSpacingSequence[],
  selectedCandidateIndex: number
): PeriodSpacingSequence | null {
  if (candidates.length === 0) return null;
  if (selectedCandidateIndex < 0 || selectedCandidateIndex >= candidates.length) return candidates[0];
  return candidates[selectedCandidateIndex];
}

function parsePeakPoints(result: AnalysisResult): SpectrumPoint[] {
  const traces = result.plots.echelle.data as Array<{ text?: unknown }>;
  const text = traces.flatMap((trace) => (Array.isArray(trace?.text) ? trace.text : []));
  const points: SpectrumPoint[] = [];

  for (const item of text) {
    if (typeof item !== "string") continue;
    const periodMatch = item.match(/P=([0-9.eE+-]+) d/);
    const amplitudeMatch = item.match(/A=([0-9.eE+-]+)/);
    if (!periodMatch || !amplitudeMatch) continue;

    const period = Number(periodMatch[1]);
    const amplitude = Number(amplitudeMatch[1]);

    if (!Number.isFinite(period) || !Number.isFinite(amplitude)) continue;
    points.push({ period, amplitude });
  }

  points.sort((a, b) => a.period - b.period);
  return points;
}

function parseFullSpectrumSeries(result: AnalysisResult): SpectrumSeries | null {
  const trace = result.plots.spectrum?.data[0] as { mode?: unknown; x?: unknown; y?: unknown } | undefined;
  if (!Array.isArray(trace?.x) || !Array.isArray(trace?.y)) return null;

  const count = Math.min(trace.x.length, trace.y.length);
  const points: SpectrumPoint[] = [];

  for (let index = 0; index < count; index += 1) {
    const period = Number(trace.x[index]);
    const amplitude = Number(trace.y[index]);
    if (Number.isFinite(period) && Number.isFinite(amplitude)) {
      points.push({ period, amplitude });
    }
  }

  points.sort((a, b) => a.period - b.period);
  return points.length > 0 ? { points, continuous: trace.mode === "lines" } : null;
}

function getCandidatePeriodRange(candidate: PeriodSpacingSequence): [number, number] | undefined {
  if (candidate.periods.length < 2) return undefined;
  const min = minValue(candidate.periods);
  const max = maxValue(candidate.periods);
  return min < max ? [min, max] : undefined;
}

function filterPointsInRange(points: SpectrumPoint[], range: [number, number] | undefined): SpectrumPoint[] {
  if (!range) return points;
  const [min, max] = range;
  const filtered = points.filter((point) => point.period >= min && point.period <= max);
  return filtered.length > 0 ? filtered : points;
}

function buildPanelA(
  spectrumPoints: SpectrumPoint[],
  peakPoints: SpectrumPoint[],
  candidate: PeriodSpacingSequence,
  sequencePeriodRange: [number, number] | undefined,
  hasContinuousSpectrum: boolean
): Array<Record<string, unknown>> {
  const visibleSpectrumPoints = filterPointsInRange(spectrumPoints, sequencePeriodRange);
  const visiblePeakPoints = filterPointsInRange(peakPoints, sequencePeriodRange);
  const selected = candidate.periods.map((period) => ({
    period,
    amplitude: findNearestAmplitude(visiblePeakPoints.length > 0 ? visiblePeakPoints : visibleSpectrumPoints, period)
  }));
  const guidePoints = selected.length > 0 ? selected : visiblePeakPoints;
  const yMin = minValue(visibleSpectrumPoints.map((point) => point.amplitude));
  const yMax = maxValue(visibleSpectrumPoints.map((point) => point.amplitude));
  const guideBase = Number.isFinite(yMin) ? Math.min(0, yMin) : 0;
  const minGuideHeight = Math.max((Number.isFinite(yMax) ? yMax - guideBase : 1) * 0.08, Number.EPSILON);
  const guideTop = Math.max(maxValue(guidePoints.map((point) => point.amplitude)) * 1.08, guideBase + minGuideHeight);

  return [
    {
      type: "scatter",
      mode: "lines",
      x: visibleSpectrumPoints.map((point) => point.period),
      y: visibleSpectrumPoints.map((point) => point.amplitude),
      xaxis: "x",
      yaxis: "y",
      line: { color: "#191919", width: 1.05 },
      marker: { color: "rgba(82, 82, 82, 0.5)", size: 3 },
      name: hasContinuousSpectrum ? "spectrum" : "peak envelope"
    },
    {
      type: "scatter",
      mode: "lines",
      x: guidePoints.flatMap((point) => [point.period, point.period, null]),
      y: guidePoints.flatMap(() => [guideBase, guideTop, null]),
      xaxis: "x",
      yaxis: "y",
      line: { color: "#2f49d9", width: 1.25, dash: "dash" },
      opacity: 0.82,
      name: "guides",
      showlegend: false,
      hoverinfo: "skip"
    },
    {
      type: "scatter",
      mode: "markers",
      x: visiblePeakPoints.map((point) => point.period),
      y: visiblePeakPoints.map((point) => point.amplitude),
      xaxis: "x",
      yaxis: "y",
      marker: { color: "#bf1e2d", size: 4.5, opacity: 0.92 },
      name: "peaks"
    },
    {
      type: "scatter",
      mode: "markers",
      x: selected.map((point) => point.period),
      y: selected.map((point) => point.amplitude),
      xaxis: "x",
      yaxis: "y",
      marker: { color: "#2643d8", size: 9, symbol: "cross", line: { color: "#1a2aa0", width: 0.5 } },
      name: "sequence"
    }
  ];
}

function buildPanelB(candidate: PeriodSpacingSequence, periodRange?: [number, number]): Array<Record<string, unknown>> {
  const periods = candidate.periods;
  const orders = candidate.radial_orders;
  const periodMid: number[] = [];
  const deltaPSeconds: number[] = [];

  for (let index = 0; index < periods.length - 1; index += 1) {
    const gap = orders[index + 1] - orders[index];
    if (gap <= 0) continue;
    periodMid.push((periods[index] + periods[index + 1]) / 2);
    deltaPSeconds.push(((periods[index + 1] - periods[index]) / gap) * 86400);
  }

  const traces: Array<Record<string, unknown>> = [
    {
      type: "scatter",
      mode: "markers",
      x: periodMid,
      y: deltaPSeconds,
      xaxis: "x2",
      yaxis: "y2",
      marker: { color: "#2a3ac9", size: 9.5, symbol: "cross", line: { color: "#1d2aa5", width: 0.5 } },
      name: "observed"
    }
  ];

  if (periodMid.length >= 2) {
    const pRef = mean(periodMid);
    const xLineStart = periodRange?.[0] ?? minValue(periodMid);
    const xLineEnd = periodRange?.[1] ?? maxValue(periodMid);
    const xLine = linspace(xLineStart, xLineEnd, 160);
    const slope = candidate.slope ?? 0;

    const center = xLine.map((value) => (candidate.delta_p_mid + slope * (value - pRef)) * 86400);
    const lower = xLine.map((value) => (candidate.delta_p_start + slope * (value - pRef)) * 86400);
    const upper = xLine.map((value) => (candidate.delta_p_end + slope * (value - pRef)) * 86400);

    traces.push(
      {
        type: "scatter",
        mode: "lines",
        x: xLine,
        y: center,
        xaxis: "x2",
        yaxis: "y2",
        line: { color: "#1a1a1a", width: 1.8, dash: "dash" },
        name: "fit"
      },
      {
        type: "scatter",
        mode: "lines",
        x: xLine,
        y: lower,
        xaxis: "x2",
        yaxis: "y2",
        line: { color: "#8c8c8c", width: 1.3, dash: "dot" },
        name: "bound",
        showlegend: false
      },
      {
        type: "scatter",
        mode: "lines",
        x: xLine,
        y: upper,
        xaxis: "x2",
        yaxis: "y2",
        line: { color: "#8c8c8c", width: 1.3, dash: "dot" },
        name: "bound",
        showlegend: false
      }
    );
  }

  return traces;
}

function buildPanelC(
  spectrumPoints: SpectrumPoint[],
  candidate: PeriodSpacingSequence,
  periodRange?: [number, number]
): Array<Record<string, unknown>> {
  const deltaP0 = candidate.delta_p_mid * 86400;
  const p0 = getShiftedInterceptSeconds(candidate);

  const allX = spectrumPoints.map((point) => point.period);
  const allY = spectrumPoints.map((point) => {
    const periodSeconds = point.period * 86400;
    const nPrime = Math.round((periodSeconds - p0) / deltaP0);
    return periodSeconds - (p0 + deltaP0 * nPrime);
  });

  const selectedX = candidate.periods;
  const selectedY = candidate.residuals.map((residual) => residual * 86400);

  const selectedSizes = selectedX.map((period) => {
    const amplitude = findNearestAmplitude(spectrumPoints, period);
    return mapAmplitudeToSize(amplitude, spectrumPoints);
  });

  const xMin = periodRange?.[0] ?? minValue(allX);
  const xMax = periodRange?.[1] ?? maxValue(allX);

  return [
    {
      type: "scatter",
      mode: "markers",
      x: allX,
      y: allY,
      xaxis: "x3",
      yaxis: "y3",
      marker: { color: "#121212", size: 3, opacity: 0.9 },
      name: "all peaks"
    },
    {
      type: "scatter",
      mode: "markers",
      x: selectedX,
      y: selectedY,
      xaxis: "x3",
      yaxis: "y3",
      marker: { color: "#2340d0", size: selectedSizes, symbol: "cross", line: { color: "#1b2da3", width: 0.5 } },
      name: "sequence"
    },
    {
      type: "scatter",
      mode: "lines",
      x: [xMin, xMax],
      y: [0, 0],
      xaxis: "x3",
      yaxis: "y3",
      line: { color: "#8c8c8c", width: 1.2 },
      name: "reference",
      showlegend: false,
      hoverinfo: "skip"
    }
  ];
}

function getShiftedInterceptSeconds(candidate: PeriodSpacingSequence): number {
  const firstPeriod = candidate.periods[0];
  if (firstPeriod === undefined) return candidate.p0 * 86400;

  const firstResidual = candidate.residuals[0] ?? 0;
  const firstOrder = candidate.radial_orders[0] ?? 0;
  return (firstPeriod - firstResidual - candidate.delta_p_mid * firstOrder) * 86400;
}

function mean(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function minValue(values: number[]): number {
  let result = Number.POSITIVE_INFINITY;
  for (const value of values) {
    if (value < result) result = value;
  }
  return result;
}

function maxValue(values: number[]): number {
  let result = Number.NEGATIVE_INFINITY;
  for (const value of values) {
    if (value > result) result = value;
  }
  return result;
}

function linspace(start: number, end: number, count: number): number[] {
  if (count <= 1) return [start];
  const step = (end - start) / (count - 1);
  return Array.from({ length: count }, (_, index) => start + index * step);
}

function findNearestAmplitude(points: SpectrumPoint[], period: number): number {
  let nearest = points[0];
  let bestDistance = Math.abs(nearest.period - period);

  for (let index = 1; index < points.length; index += 1) {
    const current = points[index];
    const distance = Math.abs(current.period - period);
    if (distance < bestDistance) {
      nearest = current;
      bestDistance = distance;
    }
  }

  return nearest.amplitude;
}

function mapAmplitudeToSize(amplitude: number, points: SpectrumPoint[]): number {
  const amplitudes = points.map((point) => point.amplitude);
  const minAmp = Math.min(...amplitudes);
  const maxAmp = Math.max(...amplitudes);

  if (maxAmp <= minAmp) return 8;

  const ratio = (amplitude - minAmp) / (maxAmp - minAmp);
  return 6 + ratio * 6;
}
