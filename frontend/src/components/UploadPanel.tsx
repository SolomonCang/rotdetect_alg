import { useEffect, useState } from "react";
import { Play, Upload, Save } from "lucide-react";
import type { SearchConfig } from "../types";
import { saveConfigToServer } from "../api";

type UploadPanelProps = {
  file: File | null;
  config: SearchConfig;
  isRunning: boolean;
  onFileChange: (file: File | null) => void;
  onConfigChange: (config: SearchConfig) => void;
  onAnalyze: () => void;
};

type NumericConfigKey = keyof Omit<SearchConfig, "frequency_column" | "amplitude_column" | "spectrum_background_path">;

type ColumnOption = {
  value: string;
  label: string;
};

const fields: Array<{ key: NumericConfigKey; label: string; step: string }> = [
  { key: "period_min", label: "P min [d]", step: "0.01" },
  { key: "period_max", label: "P max [d]", step: "0.01" },
  { key: "delta_p_min", label: "Delta_P min [s]", step: "1" },
  { key: "delta_p_max", label: "Delta_P max [s]", step: "1" },
  { key: "delta_p_grid", label: "Grid [s]", step: "0.1" },
  { key: "min_modes", label: "Min modes", step: "1" },
  { key: "max_peaks", label: "Max peaks", step: "10" },
  { key: "tolerance_fraction", label: "Tolerance", step: "0.01" },
  { key: "snr_threshold", label: "S/N threshold", step: "0.1" }
];

export function UploadPanel({
  file,
  config,
  isRunning,
  onFileChange,
  onConfigChange,
  onAnalyze
}: UploadPanelProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [columnOptions, setColumnOptions] = useState<ColumnOption[]>([]);
  const [columnMessage, setColumnMessage] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;

    async function inspectFileColumns(nextFile: File) {
      try {
        const text = await nextFile.text();
        if (!isCurrent) return;
        const options = inferColumnOptions(text);
        setColumnOptions(options);
        setColumnMessage(options.length > 0 ? null : "未能识别列，请确认文件格式");

        if (options.length > 0) {
          const values = new Set(options.map((option) => option.value));
          const nextFrequencyColumn = config.frequency_column && values.has(config.frequency_column)
            ? config.frequency_column
            : options[0]?.value;
          const nextAmplitudeColumn = config.amplitude_column && values.has(config.amplitude_column)
            ? config.amplitude_column
            : options[1]?.value ?? options[0]?.value;

          if (nextFrequencyColumn !== config.frequency_column || nextAmplitudeColumn !== config.amplitude_column) {
            onConfigChange({
              ...config,
              frequency_column: nextFrequencyColumn,
              amplitude_column: nextAmplitudeColumn
            });
          }
        }
      } catch (err) {
        if (!isCurrent) return;
        setColumnOptions([]);
        setColumnMessage(err instanceof Error ? err.message : "读取文件列失败");
      }
    }

    if (!file) {
      setColumnOptions([]);
      setColumnMessage(null);
      return;
    }

    inspectFileColumns(file);
    return () => {
      isCurrent = false;
    };
  }, [file]);

  async function handleSaveConfig() {
    setIsSaving(true);
    setSaveMessage(null);
    try {
      await saveConfigToServer(config);
      setSaveMessage({ type: "success", text: "参数已保存" });
      setTimeout(() => setSaveMessage(null), 2000);
    } catch (err) {
      setSaveMessage({
        type: "error",
        text: err instanceof Error ? err.message : "保存失败"
      });
      setTimeout(() => setSaveMessage(null), 3000);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <aside className="control-panel">
      <div>
        <h1>RotDetect</h1>
        <p>单颗星 g 模周期间隔快速探测</p>
      </div>

      <label className="drop-zone">
        <Upload size={22} />
        <span>{file ? file.name : "上传 period/frequency 表格（CSV 或 DAT）"}</span>
        <input
          type="file"
          accept=".csv,.dat,.txt,text/csv,text/plain"
          onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
        />
      </label>

      {columnOptions.length > 0 ? (
        <div className="column-grid">
          <label className="field">
            <span>Frequency column</span>
            <select
              value={config.frequency_column ?? columnOptions[0]?.value ?? ""}
              onChange={(event) => onConfigChange({ ...config, frequency_column: event.target.value })}
            >
              {columnOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Amplitude column</span>
            <select
              value={config.amplitude_column ?? columnOptions[1]?.value ?? columnOptions[0]?.value ?? ""}
              onChange={(event) => onConfigChange({ ...config, amplitude_column: event.target.value })}
            >
              {columnOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>
      ) : null}

      {columnMessage ? <div className="column-message">{columnMessage}</div> : null}

      <label className="field">
        <span>a 图背景文件</span>
        <input
          type="text"
          placeholder="默认使用输入数据；例如 examples/KIC004253413_FFT_results.dat"
          value={config.spectrum_background_path ?? ""}
          onChange={(event) => {
            const value = event.target.value.trim();
            onConfigChange({
              ...config,
              spectrum_background_path: value.length > 0 ? value : undefined
            });
          }}
        />
      </label>

      <div className="field-grid">
        {fields.map((field) => (
          <label key={field.key} className="field">
            <span>{field.label}</span>
            <input
              type="number"
              step={field.step}
              value={
                field.key.startsWith("delta_p")
                  ? ((config[field.key] as number) * 86400).toFixed(2)
                  : config[field.key]
              }
              onChange={(event) => {
                let value: number | string;
                if (field.key === "min_modes" || field.key === "max_peaks" || field.key === "top_k_candidates") {
                  value = Number.parseInt(event.target.value, 10);
                } else {
                  const numValue = Number.parseFloat(event.target.value);
                  value = field.key.startsWith("delta_p") ? numValue / 86400 : numValue;
                }
                onConfigChange({ ...config, [field.key]: Number.isFinite(value as number) ? value : config[field.key] });
              }}
            />
          </label>
        ))}
      </div>

      {saveMessage && (
        <div className={`save-message ${saveMessage.type}`}>
          {saveMessage.type === "success" ? "✓ " : "✕ "}
          {saveMessage.text}
        </div>
      )}

      <div className="action-section">
        <button 
          className="secondary-button" 
          onClick={handleSaveConfig}
          disabled={isSaving}
          type="button"
          title="将当前参数保存到 config.json"
        >
          <Save size={18} />
          {isSaving ? "保存中..." : "保存参数"}
        </button>
        <button 
          className="secondary-button" 
          onClick={() => {
            onFileChange(null);
            onConfigChange({ ...config });
          }}
          type="button"
        >
          清空
        </button>
        <button className="primary-button" disabled={!file || isRunning} onClick={onAnalyze}>
          <Play size={18} />
          {isRunning ? "分析中..." : "分析"}
        </button>
      </div>
    </aside>
  );
}

function inferColumnOptions(text: string): ColumnOption[] {
  const firstDataLine = text.split(/\r?\n/).find((line) => line.trim().length > 0);
  if (!firstDataLine) return [];

  const commentHeader = firstDataLine.trim().startsWith("#")
    ? firstDataLine.trim().replace(/^#+\s*/, "")
    : null;
  const headerTokens = commentHeader ? splitTokens(commentHeader) : [];

  if (headerTokens.length > 0 && headerTokens.some((token) => /[a-zA-Z]/.test(token))) {
    return headerTokens.map((token, index) => ({
      value: `col${index + 1}`,
      label: `Col ${index + 1}: ${normalizeColumnLabel(token)}`
    }));
  }

  const csvHeader = firstDataLine.includes(",") ? splitCsvLine(firstDataLine) : [];
  if (csvHeader.length > 1 && csvHeader.some((token) => /[a-zA-Z]/.test(token))) {
    return csvHeader.map((token, index) => ({
      value: `col${index + 1}`,
      label: `Col ${index + 1}: ${normalizeColumnLabel(token)}`
    }));
  }

  const firstNumericLine = text.split(/\r?\n/).find((line) => {
    const trimmed = line.trim();
    return trimmed.length > 0 && !trimmed.startsWith("#");
  });
  if (!firstNumericLine) return [];

  return splitTokens(firstNumericLine).map((_, index) => ({
    value: `col${index + 1}`,
    label: `Col ${index + 1}`
  }));
}

function splitTokens(line: string): string[] {
  return line
    .split(/[\s,;]+/)
    .map((token) => token.trim())
    .filter(Boolean);
}

function splitCsvLine(line: string): string[] {
  return line
    .split(",")
    .map((token) => token.trim().replace(/^"|"$/g, ""))
    .filter(Boolean);
}

function normalizeColumnLabel(token: string): string {
  const normalized = token.trim().toLowerCase();
  if (normalized === "freq" || normalized === "frequency") return "frequency";
  if (normalized === "ampl" || normalized === "amp" || normalized === "amplitude") return "amplitude";
  if (normalized === "s/n") return "snr";
  return token.trim();
}
