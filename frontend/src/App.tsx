import { useCallback, useEffect, useState } from "react";
import { analyzeSpectrum, loadConfigFromServer } from "./api";
import { CandidateTable } from "./components/CandidateTable";
import { DiagnosticCharts } from "./components/DiagnosticCharts";
import { ResultSummary } from "./components/ResultSummary";
import { UploadPanel } from "./components/UploadPanel";
import { AnalysisResult, defaultConfig, SearchConfig } from "./types";

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [config, setConfig] = useState<SearchConfig>(defaultConfig);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const candidateCount = result?.candidates.length ?? 0;

  // Load config from server on mount
  useEffect(() => {
    loadConfigFromServer()
      .then((serverConfig) => {
        setConfig(serverConfig);
      })
      .catch(() => {
        // Silently fall back to defaultConfig if server request fails
        setConfig(defaultConfig);
      });
  }, []);

  useEffect(() => {
    if (candidateCount === 0) {
      if (selectedCandidateIndex !== 0) {
        setSelectedCandidateIndex(0);
      }
      return;
    }
    if (selectedCandidateIndex >= candidateCount) {
      setSelectedCandidateIndex(candidateCount - 1);
    }
  }, [candidateCount, selectedCandidateIndex]);

  useEffect(() => {
    if (candidateCount === 0) return;

    function isTypingTarget(target: EventTarget | null): boolean {
      if (!(target instanceof HTMLElement)) return false;
      const tag = target.tagName;
      return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (isTypingTarget(event.target)) return;

      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSelectedCandidateIndex((prev) => Math.min(prev + 1, candidateCount - 1));
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        setSelectedCandidateIndex((prev) => Math.max(prev - 1, 0));
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [candidateCount]);

  async function handleAnalyze() {
    if (!file) return;
    setIsRunning(true);
    setError(null);
    try {
      const nextResult = await analyzeSpectrum(file, config);
      setResult(nextResult);
      setSelectedCandidateIndex(0);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "分析失败");
    } finally {
      setIsRunning(false);
    }
  }

  const memoizedHandleAnalyze = useCallback(handleAnalyze, [file, config]);
  const memoizedSetFile = useCallback(setFile, []);
  const memoizedSetConfig = useCallback(setConfig, []);
  const memoizedSetSelectedCandidateIndex = useCallback(setSelectedCandidateIndex, []);

  return (
    <main className="app-shell">
      <UploadPanel
        file={file}
        config={config}
        isRunning={isRunning}
        onFileChange={memoizedSetFile}
        onConfigChange={memoizedSetConfig}
        onAnalyze={memoizedHandleAnalyze}
      />
      <section className="workspace">
        <ResultSummary result={result} error={error} />
        <CandidateTable
          candidates={result?.candidates ?? []}
          selectedIndex={selectedCandidateIndex}
          onSelect={memoizedSetSelectedCandidateIndex}
        />
        <DiagnosticCharts
          result={result}
          selectedCandidateIndex={selectedCandidateIndex}
        />
      </section>
    </main>
  );
}
