import { ImageResponse } from "next/og";

export const alt = "Управляющая компания АВЛИ в Бишкеке";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", position: "relative", overflow: "hidden", background: "#071b2d", color: "white", fontFamily: "Arial, sans-serif" }}>
      <div style={{ position: "absolute", inset: 0, display: "flex", background: "linear-gradient(135deg, #0189df 0%, #073760 55%, #071b2d 100%)" }} />
      <div style={{ position: "absolute", right: -90, top: -160, width: 620, height: 620, borderRadius: "50%", border: "80px solid rgba(67,207,104,.2)" }} />
      <div style={{ position: "absolute", right: 100, bottom: -220, width: 520, height: 520, borderRadius: "50%", border: "2px solid rgba(255,255,255,.18)" }} />
      <div style={{ position: "absolute", inset: 0, padding: "82px 92px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}><div style={{ width: 72, height: 72, borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", background: "white", color: "#0189df", fontSize: 48, fontWeight: 800 }}>А</div><div style={{ fontSize: 50, fontWeight: 800, letterSpacing: 5 }}>АВЛИ</div></div>
        <div style={{ display: "flex", flexDirection: "column", gap: 22, maxWidth: 900 }}><div style={{ color: "#78ec96", fontSize: 25, fontWeight: 700, textTransform: "uppercase", letterSpacing: 2 }}>Управляющая компания в Бишкеке</div><div style={{ display: "flex", flexDirection: "column", fontSize: 66, lineHeight: 1.06, fontWeight: 750 }}><span>Порядок в доме.</span><span>Прозрачность в управлении.</span></div></div>
      </div>
    </div>,
    size,
  );
}
