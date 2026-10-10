/** A 0–1 score as a number and a bar; the number is always shown, so the bar is never the only cue. */
export function ScoreBar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <span className="scorebar" title={`${label}: ${value.toFixed(2)}`}>
      <span className="scorebar-num">{value.toFixed(2)}</span>
      <span className="scorebar-track" aria-hidden="true">
        <span className="scorebar-fill" style={{ width: `${pct}%` }} />
      </span>
    </span>
  );
}
