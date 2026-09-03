import React from "react";
import {
  AbsoluteFill,
  Audio,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { POINTS, LINE, METRICS } from "./data";

const SANS =
  "'Inter', -apple-system, 'Helvetica Neue', Helvetica, Arial, sans-serif";
const MONO =
  "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
const INK = "#F5F5F7";
const SECONDARY = "rgba(245, 245, 247, 0.62)";
const FAINT = "rgba(245, 245, 247, 0.38)";
const GREEN = "#30D158";
const RED = "#FF453A";
const HAIRLINE = "rgba(255, 255, 255, 0.14)";
const GLASS = "rgba(255, 255, 255, 0.055)";
const ENTER = Easing.bezier(0.16, 1, 0.3, 1);
const POP = Easing.bezier(0.34, 1.56, 0.64, 1);
// Scene entrance offset: TransitionSeries plays the incoming scene from local
// frame 0 *during* the cross-dissolve, so every in-scene timing is pushed later
// by the transition length. Nothing meaningful plays under the dissolve.
const IN = 0.8;

const GRAIN =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='0.55'/%3E%3C/svg%3E\")";

const fadeIn = (frame: number, fps: number, at: number, dur = 22) =>
  interpolate(frame, [(at + IN) * fps, (at + IN) * fps + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ENTER,
  });

const rise = (frame: number, fps: number, at: number, px = 40) =>
  interpolate(frame, [(at + IN) * fps, (at + IN) * fps + 28], [px, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ENTER,
  });

const shakeX = (frame: number, fps: number, at: number) => {
  const t = frame - (at + IN) * fps;
  if (t < 0) return 0;
  return Math.sin(t * 1.1) * 15 * Math.exp(-t * 0.13);
};

// Black entrance veil: hides the scene while the cross-dissolve is running,
// then gets out of the way. Scene 1 uses a short veil as a cinematic open.
const Veil: React.FC<{ dur?: number }> = ({ dur = 24 }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, dur], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ background: "#000", opacity: o }} />;
};

const Backdrop: React.FC = () => (
  <AbsoluteFill style={{ background: "#000" }}>
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(1000px 560px at 50% -8%, rgba(48,209,88,0.10), transparent 62%), radial-gradient(900px 620px at 50% 112%, rgba(10,132,255,0.10), transparent 60%)",
      }}
    />
    <AbsoluteFill
      style={{ backgroundImage: GRAIN, opacity: 0.05, mixBlendMode: "overlay" }}
    />
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(120% 90% at 50% 45%, transparent 58%, rgba(0,0,0,0.5) 100%)",
      }}
    />
  </AbsoluteFill>
);

const Eyebrow: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      fontFamily: SANS,
      fontSize: 25,
      fontWeight: 600,
      letterSpacing: 8,
      textTransform: "uppercase",
      color: SECONDARY,
      marginBottom: 26,
    }}
  >
    {children}
  </div>
);

const H1: React.FC<{ children: React.ReactNode; color?: string; size?: number }> = ({
  children,
  color = INK,
  size = 92,
}) => (
  <div
    style={{
      fontFamily: SANS,
      fontSize: size,
      fontWeight: 700,
      letterSpacing: -3,
      lineHeight: 1.04,
      color,
    }}
  >
    {children}
  </div>
);

const Whisper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      fontFamily: SANS,
      fontSize: 31,
      fontWeight: 500,
      color: SECONDARY,
      lineHeight: 1.6,
    }}
  >
    {children}
  </div>
);

const Glass: React.FC<{ children: React.ReactNode; glow?: string }> = ({
  children,
  glow,
}) => (
  <div
    style={{
      background: GLASS,
      backdropFilter: "blur(28px) saturate(1.4)",
      WebkitBackdropFilter: "blur(28px) saturate(1.4)",
      border: `1px solid ${HAIRLINE}`,
      borderRadius: 28,
      padding: "34px 42px",
      boxShadow: glow ?? "0 30px 80px rgba(0,0,0,0.5)",
    }}
  >
    {children}
  </div>
);

const Pill: React.FC<{ children: React.ReactNode; accent?: string }> = ({
  children,
  accent = INK,
}) => (
  <div
    style={{
      fontFamily: SANS,
      fontSize: 30,
      fontWeight: 600,
      color: accent === INK ? INK : "#000",
      background: accent === INK ? "rgba(255,255,255,0.1)" : accent,
      border: `1px solid ${accent === INK ? HAIRLINE : "transparent"}`,
      borderRadius: 999,
      padding: "14px 30px",
      fontVariantNumeric: "tabular-nums",
    }}
  >
    {children}
  </div>
);

const LogoMark: React.FC<{ size?: number }> = ({ size = 104 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <rect x={1.5} y={1.5} width={21} height={21} rx={6} stroke={HAIRLINE} strokeWidth={1.2} />
    <path
      d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"
      stroke={GREEN}
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"
      stroke={GREEN}
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const DocIcon: React.FC = () => (
  <svg width={44} height={44} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
    <path
      d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
      stroke={INK}
      strokeWidth={1.6}
      strokeLinejoin="round"
    />
    <path d="M14 2v6h6" stroke={INK} strokeWidth={1.6} strokeLinejoin="round" />
  </svg>
);

const TypeLine: React.FC<{ text: string; at?: number; speed?: number }> = ({
  text,
  at = 0,
  speed = 20,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = Math.floor(
    interpolate(
      frame,
      [(at + IN) * fps, (at + IN) * fps + (text.length / speed) * fps],
      [0, text.length + 1],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      },
    ),
  );
  const cursor = frame % 18 < 10 ? 1 : 0;
  return (
    <div style={{ fontFamily: MONO, fontSize: 41, color: INK, display: "flex", alignItems: "center" }}>
      <span style={{ color: GREEN, marginRight: 18 }}>$</span>
      <span>{text.slice(0, n)}</span>
      <span
        style={{
          display: "inline-block",
          width: 23,
          height: 46,
          background: GREEN,
          marginLeft: 8,
          opacity: cursor,
          borderRadius: 3,
        }}
      />
    </div>
  );
};

const VO: React.FC<{ id: string }> = ({ id }) => (
  <Audio src={staticFile(`vo/${id}.mp3`)} />
);

/* ---------------- Scene 1 (220f ≈ 7.3s, VO 5.77s) ---------------- */
const Scene1: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: 100 }}>
      <VO id="s1" />
      <Veil dur={12} />
      <div style={{ opacity: fadeIn(frame, fps, 0.2) }}>
        <Eyebrow>The problem</Eyebrow>
      </div>
      <div style={{ opacity: fadeIn(frame, fps, 0.6), transform: `translateY(${rise(frame, fps, 0.6)}px)` }}>
        <H1>You trained a model.</H1>
      </div>
      <div style={{ height: 10 }} />
      <div style={{ opacity: fadeIn(frame, fps, 1.8), transform: `translateY(${rise(frame, fps, 1.8)}px)` }}>
        <H1 color={SECONDARY}>It remembers nothing.</H1>
      </div>
      <div style={{ height: 52 }} />
      <div style={{ opacity: fadeIn(frame, fps, 3.2) }}>
        <Whisper>How long it took — gone. What data made it — gone.</Whisper>
      </div>
      <div style={{ opacity: fadeIn(frame, fps, 4) }}>
        <Whisper>How good it is — gone.</Whisper>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- Scene 2 (310f ≈ 10.3s, VO 8.83s) ---------------- */
const PLOT_W = 920;
const PLOT_H = 470;
const PAD = { l: 64, r: 30, t: 26, b: 30 };
const px = (nx: number) => PAD.l + nx * (PLOT_W - PAD.l - PAD.r);
const py = (ny: number) => PAD.t + ny * (PLOT_H - PAD.t - PAD.b);

const Scene2: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dotsStart = (1.2 + IN) * fps;
  const lineAt = (5.4 + IN) * fps;
  const lineP = interpolate(frame, [lineAt, lineAt + 1.8 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  // Clamp trend endpoints inside the axes so the line can never leave the plot.
  const cy = (v: number) => Math.min(0.965, Math.max(0.035, v));
  const x1 = px(LINE.x1);
  const y1 = py(cy(LINE.y1));
  const x2 = px(LINE.x2);
  const y2 = py(cy(LINE.y2));
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: 90 }}>
      <VO id="s2" />
      <Veil />
      <div style={{ opacity: fadeIn(frame, fps, 0.2) }}>
        <Eyebrow>A real run · zero jargon</Eyebrow>
      </div>
      <div style={{ opacity: fadeIn(frame, fps, 0.5), transform: `translateY(${rise(frame, fps, 0.5)}px)` }}>
        <H1 size={74}>Study hours → exam score.</H1>
      </div>
      <div style={{ height: 34 }} />
      <div style={{ opacity: fadeIn(frame, fps, 0.9) }}>
        <div
          style={{
            background: GLASS,
            backdropFilter: "blur(28px)",
            border: `1px solid ${HAIRLINE}`,
            borderRadius: 28,
            padding: 26,
            boxShadow: "0 30px 80px rgba(0,0,0,0.5)",
          }}
        >
          <svg width={PLOT_W} height={PLOT_H}>
            <defs>
              <clipPath id="plotClip">
                <rect
                  x={PAD.l}
                  y={PAD.t}
                  width={PLOT_W - PAD.l - PAD.r}
                  height={PLOT_H - PAD.t - PAD.b}
                  rx={10}
                />
              </clipPath>
            </defs>
            <g clipPath="url(#plotClip)">
            {[0.25, 0.5, 0.75].map((g) => (
              <line
                key={g}
                x1={PAD.l}
                x2={PLOT_W - PAD.r}
                y1={PAD.t + g * (PLOT_H - PAD.t - PAD.b)}
                y2={PAD.t + g * (PLOT_H - PAD.t - PAD.b)}
                stroke="rgba(255,255,255,0.09)"
                strokeWidth={1.5}
              />
            ))}
            {POINTS.map((p, i) => {
              const lf = dotsStart + i * 1.6;
              const r = interpolate(frame, [lf, lf + 16], [0, 7], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: POP,
              });
              const o = interpolate(frame, [lf, lf + 9], [0, 0.8], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              return <circle key={i} cx={px(p[0])} cy={py(p[1])} r={r} fill="#FFF" opacity={o} />;
            })}
            <line
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={GREEN}
              strokeWidth={5}
              strokeLinecap="round"
              pathLength={1}
              strokeDasharray={1}
              strokeDashoffset={1 - lineP}
              style={{ filter: "drop-shadow(0 0 14px rgba(48,209,88,0.7))" }}
            />
            {lineP > 0 && (
              <>
                <circle cx={x1 + (x2 - x1) * lineP} cy={y1 + (y2 - y1) * lineP} r={13} fill={GREEN} opacity={0.22} />
                <circle cx={x1 + (x2 - x1) * lineP} cy={y1 + (y2 - y1) * lineP} r={8} fill={GREEN} />
              </>
            )}
            </g>
          </svg>
        </div>
      </div>
      <div style={{ display: "flex", gap: 18, marginTop: 28, opacity: fadeIn(frame, fps, 7.8) }}>
        <Pill accent={GREEN}>R² {METRICS.r2}</Pill>
        <Pill>300 students</Pill>
        <Pill>0.44 seconds</Pill>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- Scene 3 (276f ≈ 9.2s, VO 7.68s) ---------------- */
const Scene3: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const linkW = interpolate(frame, [(1.8 + IN) * fps, (2.8 + IN) * fps], [0, 130], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ENTER,
  });
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: 100 }}>
      <VO id="s3" />
      <Veil />
      <div style={{ opacity: fadeIn(frame, fps, 0.2) }}>
        <Eyebrow>The fix</Eyebrow>
      </div>
      <div style={{ opacity: fadeIn(frame, fps, 0.5), transform: `translateY(${rise(frame, fps, 0.5)}px)` }}>
        <H1 size={80}>One call stamps it.</H1>
      </div>
      <div style={{ height: 40 }} />
      <div style={{ opacity: fadeIn(frame, fps, 1.1), transform: `translateY(${rise(frame, fps, 1.1)}px)` }}>
        <Glass>
          <div style={{ display: "flex", alignItems: "center", gap: 26 }}>
            <DocIcon />
            <div style={{ fontFamily: MONO, fontSize: 35, color: INK }}>score_model.pkl</div>
          </div>
        </Glass>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 26, margin: "26px 0 26px 60px" }}>
        <div style={{ fontFamily: MONO, fontSize: 27, color: GREEN, opacity: fadeIn(frame, fps, 1.7) }}>
          SHA-256 LINKED
        </div>
        <div style={{ height: 3, width: linkW, background: GREEN, borderRadius: 2, boxShadow: "0 0 16px rgba(48,209,88,0.8)" }} />
      </div>
      <div style={{ opacity: fadeIn(frame, fps, 2.3), transform: `translateY(${rise(frame, fps, 2.3)}px)` }}>
        <Glass glow="0 0 70px rgba(48,209,88,0.16), 0 30px 80px rgba(0,0,0,0.5)">
          <div style={{ display: "flex", alignItems: "center", gap: 26 }}>
            <DocIcon />
            <div>
              <div style={{ fontFamily: MONO, fontSize: 32, color: INK }}>score_model.pkl.modelmeta.yaml</div>
              <div style={{ fontFamily: MONO, fontSize: 28, color: GREEN, marginTop: 8 }}>
                wall_hours · filled automatically
              </div>
            </div>
          </div>
        </Glass>
      </div>
      <div style={{ height: 32 }} />
      <div style={{ opacity: fadeIn(frame, fps, 4.2) }}>
        <Whisper>No dashboard. No server. Just two files.</Whisper>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- Scene 4 (255f ≈ 8.5s, VO 6.97s) ---------------- */
const Scene4: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const rows = [
    ["dataset", "study-hours-vs-score · 300 rows"],
    ["accuracy", `R² ${METRICS.r2} · RMSE ${METRICS.rmse}`],
    ["duration", "wall_hours 0.44s — auto"],
    ["integrity", "sha256 4e7517782b8f… · linked"],
  ];
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: 100 }}>
      <VO id="s4" />
      <Veil />
      <TypeLine text="modelmeta inspect score_model.pkl" speed={22} />
      <div style={{ height: 36 }} />
      <Glass glow="0 0 70px rgba(10,132,255,0.14), 0 30px 80px rgba(0,0,0,0.5)">
        {rows.map(([k, v], i) => (
          <div
            key={k}
            style={{
              display: "flex",
              gap: 30,
              padding: "13px 0",
              opacity: fadeIn(frame, fps, 1.6 + i * 0.8),
              transform: `translateY(${rise(frame, fps, 1.6 + i * 0.8, 22)}px)`,
            }}
          >
            <div style={{ fontFamily: MONO, fontSize: 30, color: FAINT, width: 200 }}>{k}</div>
            <div
              style={{
                fontFamily: MONO,
                fontSize: 31,
                color: i === 3 ? GREEN : INK,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {v}
            </div>
          </div>
        ))}
      </Glass>
      <div style={{ height: 30 }} />
      <div style={{ opacity: fadeIn(frame, fps, 5.6) }}>
        <Whisper>The whole story. Next to the file. Offline.</Whisper>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- Scene 5 (252f ≈ 8.4s, VO 6.37s) ---------------- */
const Scene5: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const corruptAt = 4.6;
  const corrupted = frame >= (corruptAt + IN) * fps;
  const flash = corrupted
    ? interpolate(frame, [(corruptAt + IN) * fps, (corruptAt + IN) * fps + 9], [0.45, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: 100 }}>
      <VO id="s5" />
      <Veil />
      <AbsoluteFill style={{ background: `rgba(255,69,58,${flash})` }} />
      <TypeLine text="modelmeta verify score_model.pkl" speed={22} />
      <div style={{ height: 36 }} />
      {!corrupted ? (
        <div style={{ opacity: fadeIn(frame, fps, 1.6) }}>
          <Glass glow="0 0 80px rgba(48,209,88,0.22), 0 30px 80px rgba(0,0,0,0.5)">
            <div style={{ fontFamily: SANS, fontSize: 62, fontWeight: 700, letterSpacing: -2, color: GREEN }}>
              ✓ Match · exit 0
            </div>
            <div style={{ fontFamily: SANS, fontSize: 29, color: SECONDARY, marginTop: 10 }}>
              Byte-for-byte as described. Safe to load.
            </div>
          </Glass>
        </div>
      ) : (
        <div style={{ transform: `translateX(${shakeX(frame, fps, corruptAt)}px)` }}>
          <div style={{ opacity: fadeIn(frame, fps, corruptAt + 0.05) }}>
            <Whisper>…one byte changed in transit…</Whisper>
          </div>
          <div style={{ height: 20 }} />
          <div style={{ opacity: fadeIn(frame, fps, corruptAt + 0.5) }}>
            <Glass glow="0 0 80px rgba(255,69,58,0.28), 0 30px 80px rgba(0,0,0,0.5)">
              <div style={{ fontFamily: SANS, fontSize: 58, fontWeight: 700, letterSpacing: -2, color: RED }}>
                ✗ Mismatch · exit 12
              </div>
              <div style={{ fontFamily: SANS, fontSize: 29, color: SECONDARY, marginTop: 10 }}>
                Do not load this file.
              </div>
            </Glass>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

/* ---------------- Scene 6 (186f ≈ 6.2s, VO 4.21s) ---------------- */
const Scene6: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = interpolate(frame, [IN * fps, IN * fps + 55], [0.94, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ENTER,
  });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center" }}>
      <VO id="s6" />
      <Veil />
      <div style={{ opacity: fadeIn(frame, fps, 0.2), transform: `scale(${scale})` }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 30 }}>
          <LogoMark size={110} />
        </div>
        <div style={{ fontFamily: SANS, fontSize: 112, fontWeight: 700, letterSpacing: -4, color: INK }}>
          modelmeta
        </div>
        <div style={{ height: 16 }} />
        <div style={{ fontFamily: SANS, fontSize: 40, fontWeight: 600, letterSpacing: -1, color: INK }}>
          Models forget. <span style={{ color: GREEN }}>Sidecars don&apos;t.</span>
        </div>
      </div>
      <div style={{ height: 46 }} />
      <div style={{ opacity: fadeIn(frame, fps, 2.8) }}>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 34,
            color: INK,
            background: "rgba(255,255,255,0.1)",
            border: `1px solid ${HAIRLINE}`,
            borderRadius: 999,
            padding: "20px 56px",
          }}
        >
          pip install modelmeta
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const SCENE_FRAMES = [285, 321, 452, 313, 348, 186];
const TRANSITION_FRAMES = 24;

export const Demo: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Backdrop />
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[0]}>
          <Scene1 />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />
        <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[1]}>
          <Scene2 />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />
        <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[2]}>
          <Scene3 />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />
        <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[3]}>
          <Scene4 />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />
        <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[4]}>
          <Scene5 />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />
        <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[5]}>
          <Scene6 />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
