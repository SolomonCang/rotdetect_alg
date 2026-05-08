import type { AnalysisResult, SearchConfig } from "./types";

export async function analyzeSpectrum(file: File, config: SearchConfig): Promise<AnalysisResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("config", JSON.stringify(config));

  const response = await fetch("/api/analyze", {
    method: "POST",
    body
  });

  if (!response.ok) {
    let message = `分析失败：HTTP ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail ?? payload.message ?? message;
    } catch {
      // Keep the default message.
    }
    throw new Error(message);
  }

  return response.json();
}
