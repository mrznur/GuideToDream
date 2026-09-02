/**
 * CapBackground — subtle watermark on the light page bg.
 * Very faint cap outline in the bottom-right corner only.
 */
export default function CapBackground() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: "fixed",
        bottom: -80,
        right: -80,
        width: 380,
        height: 380,
        zIndex: 0,
        pointerEvents: "none",
        opacity: 0.028,
      }}
    >
      <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%" }}>
        <polygon points="50,12 94,32 50,52 6,32"
          fill="none" stroke="#1a2d4a" strokeWidth="1.2" />
        <polygon points="50,52 78,42 78,68 50,78 22,68 22,42"
          fill="none" stroke="#1a2d4a" strokeWidth="1.0" />
        <line x1="81" y1="32" x2="81" y2="76" stroke="#1a2d4a" strokeWidth="0.8" />
        <circle cx="84" cy="76" r="5" fill="none" stroke="#1a2d4a" strokeWidth="0.8" />
        <line x1="50" y1="12" x2="50" y2="52" stroke="#1a2d4a" strokeWidth="0.5" opacity="0.6" />
        <line x1="6"  y1="32" x2="94" y2="32" stroke="#1a2d4a" strokeWidth="0.4" opacity="0.5" />
      </svg>
    </div>
  )
}
