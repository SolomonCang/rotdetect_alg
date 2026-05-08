import { useState } from "react";
import type { AnalysisResult } from "../types";
import { PlotPanel } from "./PlotPanel";

type DiagnosticChartsProps = {
  result: AnalysisResult | null;
};

const tabs = [
  { key: "echelle", label: "Echelle" },
  { key: "period_spacing", label: "P-Delta P" },
  { key: "scan", label: "Scan" }
] as const;

export function DiagnosticCharts({ result }: DiagnosticChartsProps) {
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]["key"]>("echelle");

  if (!result) return null;

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
      <PlotPanel payload={result.plots[activeTab]} />
    </section>
  );
}
