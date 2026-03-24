interface Props {
  progress: number; // 0-100
  label?: string;
}

export function ProgressBar({ progress, label }: Props) {
  const clamped = Math.min(100, Math.max(0, progress));
  return (
    <div className="progress-bar-container">
      {label && <div className="progress-label">{label}</div>}
      <div className="progress-track">
        <div
          className="progress-fill"
          style={{ width: `${clamped}%` }}
        />
      </div>
      <div className="progress-text">{clamped.toFixed(1)}%</div>
    </div>
  );
}
