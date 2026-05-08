import { Play, Upload } from "lucide-react";
import type { SearchConfig } from "../types";

type UploadPanelProps = {
  file: File | null;
  config: SearchConfig;
  isRunning: boolean;
  onFileChange: (file: File | null) => void;
  onConfigChange: (config: SearchConfig) => void;
  onAnalyze: () => void;
};

const fields: Array<{ key: keyof SearchConfig; label: string; step: string }> = [
  { key: "period_min", label: "P min [d]", step: "0.01" },
  { key: "period_max", label: "P max [d]", step: "0.01" },
  { key: "delta_p_min", label: "Delta_P min [d]", step: "0.001" },
  { key: "delta_p_max", label: "Delta_P max [d]", step: "0.001" },
  { key: "delta_p_grid", label: "Grid [d]", step: "0.0001" },
  { key: "min_modes", label: "Min modes", step: "1" },
  { key: "max_peaks", label: "Max peaks", step: "10" }
];

export function UploadPanel({
  file,
  config,
  isRunning,
  onFileChange,
  onConfigChange,
  onAnalyze
}: UploadPanelProps) {
  return (
    <aside className="control-panel">
      <div>
        <h1>RotDetect</h1>
        <p>单颗星 g 模周期间隔快速探测</p>
      </div>

      <label className="drop-zone">
        <Upload size={22} />
        <span>{file ? file.name : "上传 period 或 frequency CSV"}</span>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
        />
      </label>

      <div className="field-grid">
        {fields.map((field) => (
          <label key={field.key} className="field">
            <span>{field.label}</span>
            <input
              type="number"
              step={field.step}
              value={config[field.key]}
              onChange={(event) => {
                const value = field.key === "min_modes" || field.key === "max_peaks"
                  ? Number.parseInt(event.target.value, 10)
                  : Number.parseFloat(event.target.value);
                onConfigChange({ ...config, [field.key]: Number.isFinite(value) ? value : config[field.key] });
              }}
            />
          </label>
        ))}
      </div>

      <button className="primary-button" disabled={!file || isRunning} onClick={onAnalyze}>
        <Play size={18} />
        {isRunning ? "分析中..." : "分析"}
      </button>
    </aside>
  );
}
