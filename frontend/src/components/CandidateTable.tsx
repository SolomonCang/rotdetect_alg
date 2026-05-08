import type { PeriodSpacingSequence } from "../types";

type CandidateTableProps = {
  candidates: PeriodSpacingSequence[];
};

export function CandidateTable({ candidates }: CandidateTableProps) {
  if (candidates.length === 0) return null;

  return (
    <section className="table-section">
      <h2>候选序列</h2>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Delta_P</th>
              <th>N</th>
              <th>Coverage</th>
              <th>Confidence</th>
              <th>Slope</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((candidate, index) => (
              <tr key={`${candidate.delta_p}-${index}`}>
                <td>{index + 1}</td>
                <td>{candidate.delta_p.toFixed(6)}</td>
                <td>{candidate.n_modes}</td>
                <td>{(candidate.coverage * 100).toFixed(1)}%</td>
                <td>{candidate.confidence_score.toFixed(3)}</td>
                <td>{candidate.slope === null ? "n/a" : candidate.slope.toExponential(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
