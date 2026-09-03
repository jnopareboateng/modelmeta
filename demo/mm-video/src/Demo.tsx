import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { LINE, METRICS, POINTS } from "./data";

const SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif";
const MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
const INK = "#F5F5F7";
const SECONDARY = "rgba(245, 245, 247, 0.64)";
const MUTED = "rgba(245, 245, 247, 0.42)";
const GREEN = "#30D158";
const RED = "#FF453A";
const BLUE = "#64D2FF";
const HAIRLINE = "rgba(255, 255, 255, 0.15)";
const PANEL = "rgba(255, 255, 255, 0.055)";
const ENTER = Easing.bezier(0.16, 1, 0.3, 1);
const POP = Easing.bezier(0.34, 1.56, 0.64, 1);
const TRANSITION_FRAMES = 18;
const WAKE = 0.62;

const GRAIN =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='0.55'/%3E%3C/svg%3E\")";

const reveal = (frame: number, fps: number, at: number, duration = 20) =>
  interpolate(frame, [(at + WAKE) * fps, (at + WAKE) * fps + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ENTER,
  });

const lift = (frame: number, fps: number, at: number, distance = 28) =>
  interpolate(frame, [(at + WAKE) * fps, (at + WAKE) * fps + 24], [distance, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ENTER,
  });

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const Backdrop: React.FC = () => (
  <AbsoluteFill style={{ background: "#000" }}>
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(900px 520px at 50% -4%, rgba(48,209,88,0.11), transparent 65%), radial-gradient(760px 520px at 50% 112%, rgba(10,132,255,0.09), transparent 65%)",
      }}
    />
    <AbsoluteFill style={{ backgroundImage: GRAIN, opacity: 0.045, mixBlendMode: "overlay" }} />
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(125% 92% at 50% 45%, transparent 54%, rgba(0,0,0,0.58) 100%)",
      }}
    />
  </AbsoluteFill>
);

const SceneVeil: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{
        background: "#000",
        opacity: interpolate(frame, [0, TRANSITION_FRAMES], [1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        }),
      }}
    />
  );
};

const Eyebrow: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color = SECONDARY }) => (
  <div
    style={{
      fontFamily: SANS,
      fontSize: 22,
      fontWeight: 600,
      letterSpacing: 7,
      textTransform: "uppercase",
      color,
      marginBottom: 24,
    }}
  >
    {children}
  </div>
);

const H1: React.FC<{ children: React.ReactNode; size?: number; color?: string }> = ({
  children,
  size = 82,
  color = INK,
}) => (
  <div
    style={{
      fontFamily: SANS,
      fontSize: size,
      fontWeight: 700,
      letterSpacing: -3.5,
      lineHeight: 1.02,
      color,
    }}
  >
    {children}
  </div>
);

const Body: React.FC<{ children: React.ReactNode; color?: string; size?: number }> = ({
  children,
  color = SECONDARY,
  size = 30,
}) => (
  <div style={{ fontFamily: SANS, fontSize: size, fontWeight: 500, color, lineHeight: 1.45 }}>
    {children}
  </div>
);

const Glass: React.FC<{ children: React.ReactNode; glow?: string; style?: React.CSSProperties }> = ({
  children,
  glow,
  style,
}) => (
  <div
    style={{
      background: PANEL,
      border: `1px solid ${HAIRLINE}`,
      borderRadius: 28,
      boxShadow: glow ?? "0 30px 90px rgba(0,0,0,0.48)",
      backdropFilter: "blur(24px) saturate(1.25)",
      WebkitBackdropFilter: "blur(24px) saturate(1.25)",
      ...style,
    }}
  >
    {children}
  </div>
);

const Pill: React.FC<{ children: React.ReactNode; accent?: "green" | "blue" | "neutral" }> = ({
  children,
  accent = "neutral",
}) => {
  const green = accent === "green";
  const blue = accent === "blue";
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        padding: "13px 24px",
        borderRadius: 999,
        border: `1px solid ${green ? "transparent" : blue ? "rgba(100,210,255,0.30)" : HAIRLINE}`,
        background: green ? GREEN : blue ? "rgba(100,210,255,0.10)" : "rgba(255,255,255,0.085)",
        color: green ? "#061107" : blue ? BLUE : INK,
        fontFamily: SANS,
        fontSize: 25,
        fontWeight: 600,
        fontVariantNumeric: "tabular-nums",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </div>
  );
};

const LinkMark: React.FC<{ size?: number; color?: string }> = ({ size = 48, color = GREEN }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const FileMark: React.FC<{ color?: string }> = ({ color = INK }) => (
  <svg width={48} height={48} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke={color} strokeWidth={1.45} strokeLinejoin="round" />
    <path d="M14 2v6h6" stroke={color} strokeWidth={1.45} strokeLinejoin="round" />
  </svg>
);

const CheckMark: React.FC<{ color?: string; size?: number }> = ({ color = GREEN, size = 32 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path d="m5 12.5 4.4 4.4L19 7.3" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const TypeLine: React.FC<{ command: string; sceneAt?: number }> = ({ command, sceneAt = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const typed = Math.floor(
    interpolate(frame, [(sceneAt + WAKE) * fps, (sceneAt + WAKE) * fps + (command.length / 25) * fps], [0, command.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.linear,
    }),
  );
  const cursorVisible = frame % 18 < 11;
  return (
    <div style={{ display: "flex", alignItems: "center", fontFamily: MONO, fontSize: 32, color: INK }}>
      <span style={{ color: GREEN, marginRight: 14 }}>$</span>
      <span>{command.slice(0, typed)}</span>
      <span style={{ width: 17, height: 34, marginLeft: 7, borderRadius: 2, background: GREEN, opacity: cursorVisible ? 1 : 0 }} />
    </div>
  );
};

const Voice: React.FC<{ id: string }> = ({ id }) => (
  <Sequence from={TRANSITION_FRAMES} layout="none">
    <Audio src={staticFile(`vo/${id}.mp3`)} volume={0.98} />
  </Sequence>
);

const Sfx: React.FC<{ id: string; from: number; volume?: number }> = ({ id, from, volume = 0.2 }) => (
  <Sequence from={Math.round(from * 30) + TRANSITION_FRAMES} layout="none">
    <Audio src={staticFile(`sfx/${id}.wav`)} volume={volume} />
  </Sequence>
);

const Scene1: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ padding: 96, justifyContent: "center" }}>
      <Voice id="s1" />
      <Sfx id="pulse" from={0.2} volume={0.18} />
      <SceneVeil />
      <div style={{ opacity: reveal(frame, fps, 0.05) }}><Eyebrow>The problem</Eyebrow></div>
      <div style={{ opacity: reveal(frame, fps, 0.35), translate: `0px ${lift(frame, fps, 0.35)}px` }}><H1>Every model has a story.</H1></div>
      <div style={{ height: 20 }} />
      <div style={{ opacity: reveal(frame, fps, 1.35), translate: `0px ${lift(frame, fps, 1.35)}px` }}><H1 color={SECONDARY}>It rarely travels with the weights.</H1></div>
      <div style={{ height: 58 }} />
      <div style={{ opacity: reveal(frame, fps, 2.7), translate: `0px ${lift(frame, fps, 2.7)}px` }}>
        <Glass style={{ padding: "26px 30px" }}>
          <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
            <FileMark color={MUTED} />
            <div style={{ fontFamily: MONO, fontSize: 27, color: INK }}>score_model.pkl</div>
            <div style={{ flex: 1 }} />
            {["data", "score", "time"].map((label, index) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: index ? 18 : 0 }}>
                <div style={{ width: 8, height: 8, borderRadius: 99, background: RED, boxShadow: `0 0 12px ${RED}` }} />
                <div style={{ fontFamily: MONO, fontSize: 21, color: MUTED }}>{label}</div>
              </div>
            ))}
          </div>
        </Glass>
      </div>
      <div style={{ height: 30 }} />
      <div style={{ opacity: reveal(frame, fps, 4.15) }}><Body>Context gets lost between the checkpoint and the next person.</Body></div>
    </AbsoluteFill>
  );
};

const CHART_W = 888;
const CHART_H = 390;
const AXIS = { left: 56, right: 26, top: 28, bottom: 44 };
const plotWidth = CHART_W - AXIS.left - AXIS.right;
const plotHeight = CHART_H - AXIS.top - AXIS.bottom;
const plotX = (value: number) => AXIS.left + value * plotWidth;
const plotY = (value: number) => AXIS.top + value * plotHeight;

const Scene2: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dotsStart = (1.1 + WAKE) * fps;
  const lineStart = (4.8 + WAKE) * fps;
  const progress = interpolate(frame, [lineStart, lineStart + 1.8 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const startX = plotX(clamp(LINE.x1, 0.025, 0.975));
  const endX = plotX(clamp(LINE.x2, 0.025, 0.975));
  const startY = plotY(clamp(LINE.y1, 0.06, 0.94));
  const endY = plotY(clamp(LINE.y2, 0.06, 0.94));
  const travelerX = startX + (endX - startX) * progress;
  const travelerY = startY + (endY - startY) * progress;
  return (
    <AbsoluteFill style={{ padding: "72px 96px 68px", justifyContent: "center" }}>
      <Voice id="s2" />
      <Sfx id="click" from={1.2} volume={0.12} />
      <Sfx id="link" from={5.9} volume={0.18} />
      <SceneVeil />
      <div style={{ opacity: reveal(frame, fps, 0.05) }}><Eyebrow>A real run · zero jargon</Eyebrow></div>
      <div style={{ opacity: reveal(frame, fps, 0.35), translate: `0px ${lift(frame, fps, 0.35)}px` }}><H1 size={72}>Study hours <span style={{ color: GREEN }}>→</span> exam score.</H1></div>
      <div style={{ height: 25 }} />
      <div style={{ opacity: reveal(frame, fps, 0.75), translate: `0px ${lift(frame, fps, 0.75, 18)}px` }}>
        <Glass style={{ padding: "24px 24px 18px", overflow: "hidden" }}>
          <svg width="100%" height={CHART_H} viewBox={`0 0 ${CHART_W} ${CHART_H}`}>
            <defs><clipPath id="bounded-plot"><rect x={AXIS.left} y={AXIS.top} width={plotWidth} height={plotHeight} rx={12} /></clipPath></defs>
            <g clipPath="url(#bounded-plot)">
              {[0.2, 0.4, 0.6, 0.8].map((value) => (
                <line key={value} x1={AXIS.left} x2={CHART_W - AXIS.right} y1={plotY(value)} y2={plotY(value)} stroke="rgba(255,255,255,0.10)" strokeWidth={1} />
              ))}
              {POINTS.map((point, index) => {
                const at = dotsStart + index * 1.15;
                const radius = interpolate(frame, [at, at + 14], [0, 6.5], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: POP });
                const opacity = interpolate(frame, [at, at + 8], [0, 0.78], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
                return <circle key={index} cx={plotX(point[0])} cy={plotY(point[1])} r={radius} fill={INK} opacity={opacity} />;
              })}
              <line x1={startX} y1={startY} x2={endX} y2={endY} stroke={GREEN} strokeWidth={18} opacity={0.14} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - progress} />
              <line x1={startX} y1={startY} x2={endX} y2={endY} stroke={GREEN} strokeWidth={4} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - progress} />
              {progress > 0 && <circle cx={travelerX} cy={travelerY} r={7} fill={GREEN} />}
            </g>
            <text x={AXIS.left} y={CHART_H - 10} fill={MUTED} fontFamily={MONO} fontSize={17}>STUDY HOURS</text>
            <text x={CHART_W - AXIS.right} y={AXIS.top - 8} fill={MUTED} fontFamily={MONO} fontSize={17} textAnchor="end">EXAM SCORE</text>
          </svg>
        </Glass>
      </div>
      <div style={{ display: "flex", gap: 14, marginTop: 22, opacity: reveal(frame, fps, 7.35) }}>
        <Pill accent="green">R² {METRICS.r2}</Pill><Pill accent="blue">300 students</Pill><Pill>0.44 seconds</Pill>
      </div>
    </AbsoluteFill>
  );
};

const Scene3: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const linkProgress = interpolate(frame, [(2.0 + WAKE) * fps, (2.8 + WAKE) * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ENTER });
  return (
    <AbsoluteFill style={{ padding: 96, justifyContent: "center" }}>
      <Voice id="s3" /><Sfx id="click" from={0.85} volume={0.13} /><Sfx id="link" from={3.0} volume={0.24} /><SceneVeil />
      <div style={{ opacity: reveal(frame, fps, 0.05) }}><Eyebrow>The fix</Eyebrow></div>
      <div style={{ opacity: reveal(frame, fps, 0.35), translate: `0px ${lift(frame, fps, 0.35)}px` }}><H1 size={78}>One call stamps it.</H1></div>
      <div style={{ height: 42 }} />
      <div style={{ opacity: reveal(frame, fps, 1.0), translate: `0px ${lift(frame, fps, 1.0)}px` }}><Glass style={{ padding: "27px 34px" }}><TypeLine command="modelmeta stamp score_model.pkl" sceneAt={1.0} /></Glass></div>
      <div style={{ height: 28 }} />
      <div style={{ position: "relative", height: 276 }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 0, opacity: reveal(frame, fps, 2.0), translate: `0px ${lift(frame, fps, 2.0)}px` }}>
          <Glass style={{ padding: "24px 30px" }}><div style={{ display: "flex", alignItems: "center", gap: 18 }}><FileMark /><div style={{ fontFamily: MONO, fontSize: 30, color: INK }}>score_model.pkl</div><div style={{ flex: 1 }} /><div style={{ fontFamily: MONO, fontSize: 20, color: MUTED }}>WEIGHTS</div></div></Glass>
        </div>
        <div style={{ position: "absolute", left: 50, right: 0, top: 144, opacity: reveal(frame, fps, 2.55), translate: `0px ${lift(frame, fps, 2.55)}px` }}>
          <Glass glow="0 0 80px rgba(48,209,88,0.16), 0 30px 90px rgba(0,0,0,0.48)" style={{ padding: "24px 30px" }}><div style={{ display: "flex", alignItems: "center", gap: 18 }}><LinkMark /><div><div style={{ fontFamily: MONO, fontSize: 28, color: INK }}>score_model.pkl.modelmeta.yaml</div><div style={{ fontFamily: MONO, fontSize: 22, color: GREEN, marginTop: 7 }}>SHA-256 LINKED · AUTO-TIMED</div></div></div></Glass>
        </div>
        <div style={{ position: "absolute", left: 82, top: 118, width: 2, height: 52, background: GREEN, transformOrigin: "top", scale: `1 ${linkProgress}`, opacity: linkProgress }} />
      </div>
      <div style={{ marginTop: 14, opacity: reveal(frame, fps, 5.1) }}><Body>No dashboard. No server. Just two files.</Body></div>
    </AbsoluteFill>
  );
};

const MetaRow: React.FC<{ label: string; value: string; accent?: string; at: number }> = ({ label, value, accent = INK, at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return <div style={{ display: "flex", alignItems: "baseline", gap: 26, padding: "15px 0", borderBottom: `1px solid rgba(255,255,255,0.08)`, opacity: reveal(frame, fps, at), translate: `0px ${lift(frame, fps, at, 20)}px` }}><div style={{ width: 170, flexShrink: 0, fontFamily: MONO, fontSize: 22, color: MUTED }}>{label}</div><div style={{ fontFamily: MONO, fontSize: 25, color: accent, fontVariantNumeric: "tabular-nums" }}>{value}</div></div>;
};

const Scene4: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ padding: 96, justifyContent: "center" }}>
      <Voice id="s4" /><Sfx id="click" from={0.75} volume={0.13} /><SceneVeil />
      <div style={{ opacity: reveal(frame, fps, 0.05) }}><Eyebrow>Readable anywhere</Eyebrow></div>
      <div style={{ opacity: reveal(frame, fps, 0.35), translate: `0px ${lift(frame, fps, 0.35)}px` }}><TypeLine command="modelmeta inspect score_model.pkl" sceneAt={0.35} /></div>
      <div style={{ height: 34 }} />
      <div style={{ opacity: reveal(frame, fps, 0.85), translate: `0px ${lift(frame, fps, 0.85)}px` }}>
        <Glass glow="0 0 70px rgba(100,210,255,0.11), 0 30px 90px rgba(0,0,0,0.48)" style={{ padding: "18px 32px 10px" }}>
          <MetaRow label="dataset" value="study-hours-vs-score · 300 rows" at={1.05} />
          <MetaRow label="accuracy" value={`R² ${METRICS.r2} · RMSE ${METRICS.rmse}`} at={1.55} />
          <MetaRow label="duration" value="wall_hours 0.44s · automatic" at={2.05} />
          <MetaRow label="integrity" value="sha256 4e7517782b8f… · linked" accent={GREEN} at={2.55} />
        </Glass>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 13, marginTop: 28, opacity: reveal(frame, fps, 4.25) }}><CheckMark size={28} /><Body color={INK}>The whole story. Next to the file. Offline.</Body></div>
    </AbsoluteFill>
  );
};

const Scene5: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const changedAt = 3.05;
  const lockupAt = 5.6;
  const changed = frame >= (changedAt + WAKE) * fps;
  const lockupOpacity = reveal(frame, fps, lockupAt);
  const topOpacity = interpolate(
    frame,
    [(lockupAt + WAKE - 0.18) * fps, (lockupAt + WAKE + 0.38) * fps],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ENTER },
  );
  const statusOpacity = interpolate(
    frame,
    [(lockupAt + WAKE - 0.18) * fps, (lockupAt + WAKE + 0.38) * fps],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ENTER },
  );
  const warningFlash = changed ? interpolate(frame, [(changedAt + WAKE) * fps, (changedAt + WAKE) * fps + 8], [0.26, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  const delta = frame - (changedAt + WAKE) * fps;
  const shake = changed ? Math.sin(delta * 1.6) * 8 * Math.exp(-delta * 0.17) : 0;
  return (
    <AbsoluteFill style={{ padding: 96, justifyContent: "center" }}>
      <Voice id="s5" /><Sfx id="click" from={0.65} volume={0.13} /><Sfx id="warning" from={changedAt} volume={0.22} /><SceneVeil />
      <AbsoluteFill style={{ background: `rgba(255,69,58,${warningFlash})` }} />
      <div style={{ opacity: topOpacity }}>
        <div style={{ opacity: reveal(frame, fps, 0.05) }}><Eyebrow>Before you load it</Eyebrow></div>
        <div style={{ opacity: reveal(frame, fps, 0.35), translate: `0px ${lift(frame, fps, 0.35)}px` }}><TypeLine command="modelmeta verify score_model.pkl" sceneAt={0.35} /></div>
      </div>
      <div style={{ height: 40 }} />
      <div style={{ minHeight: 260, opacity: statusOpacity, translate: `${shake}px 0px` }}>
        {!changed ? (
          <div style={{ opacity: reveal(frame, fps, 1.2) }}><Glass glow="0 0 90px rgba(48,209,88,0.20), 0 30px 90px rgba(0,0,0,0.48)" style={{ padding: "30px 34px" }}><div style={{ display: "flex", alignItems: "center", gap: 18 }}><CheckMark size={42} /><div><div style={{ fontFamily: SANS, fontSize: 52, fontWeight: 700, letterSpacing: -2, color: GREEN }}>MATCH · EXIT 0</div><div style={{ fontFamily: SANS, fontSize: 27, color: SECONDARY, marginTop: 7 }}>Byte-for-byte as described.</div></div></div></Glass></div>
        ) : (
          <div style={{ opacity: reveal(frame, fps, changedAt + 0.05) }}><Glass glow="0 0 90px rgba(255,69,58,0.21), 0 30px 90px rgba(0,0,0,0.48)" style={{ padding: "30px 34px" }}><div style={{ display: "flex", alignItems: "center", gap: 18 }}><div style={{ width: 42, height: 42, border: `2px solid ${RED}`, borderRadius: 99, display: "grid", placeItems: "center", color: RED, fontFamily: SANS, fontSize: 31 }}>×</div><div><div style={{ fontFamily: SANS, fontSize: 49, fontWeight: 700, letterSpacing: -2, color: RED }}>MISMATCH · EXIT 12</div><div style={{ fontFamily: SANS, fontSize: 27, color: SECONDARY, marginTop: 7 }}>One changed byte. The gate stops it.</div></div></div></Glass></div>
        )}
      </div>
      <div style={{ height: 26 }} />
      <AbsoluteFill style={{ left: 96, right: 96, top: 0, bottom: 0, justifyContent: "center", alignItems: "center", pointerEvents: "none" }}>
        <div style={{ opacity: lockupOpacity, translate: `0px ${lift(frame, fps, lockupAt)}px`, display: "flex", alignItems: "center", gap: 18 }}>
          <div style={{ width: 64, height: 64, border: `1px solid ${HAIRLINE}`, borderRadius: 18, display: "grid", placeItems: "center" }}><LinkMark size={39} /></div>
          <div><div style={{ fontFamily: SANS, fontSize: 39, fontWeight: 700, letterSpacing: -1.8, color: INK }}>Models forget. <span style={{ color: GREEN }}>Sidecars don&apos;t.</span></div><div style={{ marginTop: 8, fontFamily: MONO, fontSize: 23, color: SECONDARY }}>pip install modelmeta</div></div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const ProgressRail: React.FC<{ duration: number }> = ({ duration }) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, duration], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <div style={{ position: "absolute", left: 96, right: 96, bottom: 38, height: 2, background: "rgba(255,255,255,0.12)", zIndex: 10 }}><div style={{ height: 2, width: `${progress * 100}%`, background: GREEN, boxShadow: `0 0 12px ${GREEN}` }} /></div>;
};

export const SCENE_FRAMES = [195, 354, 330, 210, 330];
const TOTAL_FRAMES = SCENE_FRAMES.reduce((sum, frames) => sum + frames, 0) - TRANSITION_FRAMES * 4;

export const Demo: React.FC = () => (
  <AbsoluteFill style={{ background: "#000" }}>
    <Backdrop />
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[0]}><Scene1 /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })} />
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[1]}><Scene2 /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })} />
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[2]}><Scene3 /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })} />
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[3]}><Scene4 /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })} />
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[4]}><Scene5 /></TransitionSeries.Sequence>
    </TransitionSeries>
    <ProgressRail duration={TOTAL_FRAMES} />
  </AbsoluteFill>
);
