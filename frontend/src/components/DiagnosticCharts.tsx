import { memo, useMemo, useState } from "react";
import type { AnalysisResult } from "../types";
import { buildCandidateTriptychPayload } from "./candidateTriptych";
import { PlotPanel } from "./PlotPanel";

type DiagnosticChartsProps = {
  result: AnalysisResult | null;
  selectedCandidateIndex: number;
};

const tabs = [
  { key: "candidate_triptych", label: "Candidate diagnostics" },
  { key: "echelle", label: "Echelle" },
  { key: "period_spacing", label: "Local Delta_P" },
  { key: "scan", label: "Trend Scan" }
] as const;

function DiagnosticChartsImpl({
  result,
  selectedCandidateIndex
}: DiagnosticChartsProps) {
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]["key"]>("candidate_triptych");

  // 只在需要时计算 candidateTriptych，避免不必要的数据构建
  const candidateTriptych = useMemo(
    () => {
      if (!result || activeTab !== "candidate_triptych") return null;
      return buildCandidateTriptychPayload(result, selectedCandidateIndex);
    },
    [activeTab, result, selectedCandidateIndex]
  );

  const payload = useMemo(
    () => {
      if (!result) return null;
      if (activeTab === "candidate_triptych") {
        return candidateTriptych;
      }
      const plotKey = activeTab as "echelle" | "period_spacing" | "scan";
      return result.plots[plotKey];
    },
    [activeTab, candidateTriptych, result]
  );

  if (!result || !payload) return null;

  return (
    <section className="charts">
      <div className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={activeTab === tab.key ? "active" : ""}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <PlotPanel payload={payload} />
    </section>
  );
}

export const DiagnosticCharts = memo(DiagnosticChartsImpl);
