import { useState } from "react";
import { analyzeSpectrum } from "./api";
import { CandidateTable } from "./components/CandidateTable";
import { DiagnosticCharts } from "./components/DiagnosticCharts";
import { ResultSummary } from "./components/ResultSummary";
import { UploadPanel } from "./components/UploadPanel";
import { AnalysisResult, defaultConfig, SearchConfig } from "./types";

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [config, setConfig] = useState<SearchConfig>(defaultConfig);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  async function handleAnalyze() {
    if (!file) return;
    setIsRunning(true);
    setError(null);
    try {
      const nextResult = await analyzeSpectrum(file, config);
      setResult(nextResult);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "分析失败");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <main className="app-shell">
      <UploadPanel
        file={file}
        config={config}
        isRunning={isRunning}
        onFileChange={setFile}
        onConfigChange={setConfig}
        onAnalyze={handleAnalyze}
      />
      <section className="workspace">
        <ResultSummary result={result} error={error} />
        <CandidateTable candidates={result?.candidates ?? []} />
        <DiagnosticCharts result={result} />
      </section>
    </main>
  );
}
