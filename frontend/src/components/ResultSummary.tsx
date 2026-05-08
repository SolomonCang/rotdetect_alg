import { AlertCircle, CheckCircle2 } from "lucide-react";
import type { AnalysisResult } from "../types";

type ResultSummaryProps = {
  result: AnalysisResult | null;
  error: string | null;
};

export function ResultSummary({ result, error }: ResultSummaryProps) {
  if (error) {
    return (
      <section className="message error">
        <AlertCircle size={18} />
        <span>{error}</span>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="empty-state">
        <h2>等待输入</h2>
        <p>上传包含 period 或 frequency 单列的 CSV，然后点击分析。</p>
      </section>
    );
  }

  const best = result.best_sequence;
  return (
    <section className="summary">
      <div className="summary-header">
        <div>
          <h2>{best ? "最佳候选" : "未找到可信候选"}</h2>
          <p>{result.input_summary.n_peaks} 个峰，{result.input_summary.n_period_points} 个周期点进入搜索</p>
        </div>
        <CheckCircle2 size={22} />
      </div>

      {best ? (
        <div className="metric-grid">
          <Metric label="Delta_P" value={`${best.delta_p.toFixed(6)} d`} />
          <Metric label="N modes" value={best.n_modes.toString()} />
          <Metric label="Coverage" value={`${(best.coverage * 100).toFixed(1)}%`} />
          <Metric label="Confidence" value={best.confidence_score.toFixed(3)} />
          <Metric label="Slope" value={best.slope === null ? "n/a" : best.slope.toExponential(2)} />
          <Metric label="Delta_P error" value={best.delta_p_error === null ? "n/a" : best.delta_p_error.toExponential(2)} />
        </div>
      ) : null}

      {result.warnings.length > 0 ? (
        <div className="warnings">
          {result.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
