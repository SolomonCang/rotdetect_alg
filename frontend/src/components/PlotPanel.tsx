import { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";
import type { PlotPayload } from "../types";

type PlotPanelProps = {
  payload: PlotPayload;
};

export function PlotPanel({ payload }: PlotPanelProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    Plotly.react(ref.current, payload.data, payload.layout, {
      responsive: true,
      displaylogo: false
    });

    return () => {
      if (ref.current) {
        Plotly.purge(ref.current);
      }
    };
  }, [payload]);

  return <div className="plot-panel" ref={ref} />;
}
