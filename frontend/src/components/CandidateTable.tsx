import { memo } from "react";
import type { PeriodSpacingSequence } from "../types";

type CandidateTableProps = {
  candidates: PeriodSpacingSequence[];
  selectedIndex: number;
  onSelect: (index: number) => void;
};

function CandidateTableImpl({
  candidates,
  selectedIndex,
  onSelect
}: CandidateTableProps) {
  if (candidates.length === 0) return null;

  return (
    <section className="table-section">
      <h2>候选序列</h2>
      <p className="table-hint">使用上下方向键可切换当前查看序列</p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>View</th>
              <th>#</th>
              <th>Rep. Delta_P</th>
              <th>Start</th>
              <th>End</th>
              <th>N</th>
              <th>Coverage</th>
              <th>Confidence</th>
              <th>Amp priority</th>
              <th>Slope</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((candidate, index) => (
              <tr
                key={`${candidate.delta_p}-${index}`}
                className={index === selectedIndex ? "is-selected" : ""}
                onClick={() => onSelect(index)}
              >
                <td>
                  <span
                    className={index === selectedIndex ? "view-indicator active" : "view-indicator"}
                    aria-label={index === selectedIndex ? "current" : "not-current"}
                  />
                </td>
                <td>{index + 1}</td>
                <td>{(candidate.delta_p_mid * 86400).toFixed(2)}</td>
                <td>{(candidate.delta_p_start * 86400).toFixed(2)}</td>
                <td>{(candidate.delta_p_end * 86400).toFixed(2)}</td>
                <td>{candidate.n_modes}</td>
                <td>{(candidate.coverage * 100).toFixed(1)}%</td>
                <td>{candidate.confidence_score.toFixed(3)}</td>
                <td>{(candidate.amplitude_score * 100).toFixed(1)}%</td>
                <td>{candidate.slope === null ? "n/a" : candidate.slope.toExponential(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export const CandidateTable = memo(CandidateTableImpl);
