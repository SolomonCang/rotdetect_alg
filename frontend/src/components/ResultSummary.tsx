import { memo } from "react";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import type { AnalysisResult, AmplitudePeriodCluster } from "../types";

type ResultSummaryProps = {
  result: AnalysisResult | null;
  error: string | null;
};

function ResultSummaryImpl({ result, error }: ResultSummaryProps) {
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
          <Metric label="Representative Delta_P" value={`${(best.delta_p_mid * 86400).toFixed(2)} s`} />
          <Metric label="Delta_P start" value={`${(best.delta_p_start * 86400).toFixed(2)} s`} />
          <Metric label="Delta_P end" value={`${(best.delta_p_end * 86400).toFixed(2)} s`} />
          <Metric label="N modes" value={best.n_modes.toString()} />
          <Metric label="Coverage" value={`${(best.coverage * 100).toFixed(1)}%`} />
          <Metric label="Confidence" value={best.confidence_score.toFixed(3)} />
          <Metric label="Amp priority" value={`${(best.amplitude_score * 100).toFixed(1)}%`} />
          <Metric label="Median amp" value={best.amplitude_median.toPrecision(4)} />
          <Metric label="Slope" value={best.slope === null ? "n/a" : best.slope.toExponential(2)} />
          <Metric label="Delta_P error" value={best.delta_p_error === null ? "n/a" : (best.delta_p_error * 86400).toExponential(2)} />
        </div>
      ) : null}

      {result.amplitude_period_clusters.length > 0 ? (
        <div className="amplitude-clusters">
          <h3>振幅分层周期范围</h3>
          <div className="cluster-grid">
            {result.amplitude_period_clusters.map((cluster) => (
              <AmplitudeClusterCard key={`${cluster.label}-${cluster.rank}`} cluster={cluster} />
            ))}
          </div>
        </div>
      ) : null}

      {best ? (
        <p>
          代表 Delta_P 显示为单个摘要值；局部 Delta_P 曲线的起点和终点变化请结合上面的
          <strong> Delta_P start/end </strong>
          和下方的 <strong>P-Delta P</strong> 图一起查看。
        </p>
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

function AmplitudeClusterCard({ cluster }: { cluster: AmplitudePeriodCluster }) {
  const labelMap: Record<string, string> = {
    high: "高振幅",
    medium: "中振幅",
    low: "低振幅"
  };
  const ranges = cluster.period_ranges
    .slice(0, 3)
    .map((range) => `${range.period_min.toFixed(4)}-${range.period_max.toFixed(4)} d`)
    .join("; ");

  return (
    <article className="cluster-card">
      <div>
        <span>{labelMap[cluster.label] ?? cluster.label}</span>
        <strong>{cluster.period_min.toFixed(4)}-{cluster.period_max.toFixed(4)} d</strong>
      </div>
      <p>{cluster.n_points} 点，振幅中位数 {cluster.amplitude_median.toPrecision(4)}，占总振幅 {(cluster.amplitude_fraction * 100).toFixed(1)}%</p>
      {ranges ? <p className="cluster-ranges">{ranges}</p> : null}
    </article>
  );
}

export const ResultSummary = memo(ResultSummaryImpl);
