const LINES = [
  { y: 46, x2: 98, dark: true },
  { y: 62, x2: 84 },
  { y: 78, x2: 92 },
  { y: 94, x2: 70 },
  { y: 110, x2: 88 },
  { y: 126, x2: 60 },
];

export default function DocLoader({ label = "Loading" }: { label?: string }) {
  return (
    <div className="docloader" role="status" aria-label={label}>
      <div className="doc">
        <svg viewBox="0 0 120 156" aria-hidden="true">
          <rect x="1" y="1" width="118" height="154" rx="11" pathLength={1} className="doc-outline" />
          <circle cx="24" cy="24" r="8" pathLength={1} className="doc-outline" />
          {LINES.map((l, i) => (
            <line
              key={l.y}
              x1="22"
              y1={l.y}
              x2={l.x2}
              y2={l.y}
              pathLength={1}
              className={"doc-line" + (l.dark ? " dark" : "")}
              style={{ animationDelay: `${0.25 + i * 0.12}s` }}
            />
          ))}
        </svg>
        <div className="doc-beam" />
      </div>
      <p className="doc-label">
        {label}
        <span className="dots" />
      </p>
    </div>
  );
}