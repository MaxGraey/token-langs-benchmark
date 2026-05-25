import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createCanvas } from "canvas";

const __dirname = dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = resolve(__dirname, "..", "results");
const OUT_PATH = resolve(__dirname, "..", "media", "chart.png");

const theme = {
  bg: "#212530",
  text: "#f7f7f5",
  muted: "#989ea9",
  grid: "rgba(210, 218, 230, 0.165)",
  divider: "rgba(230, 236, 245, 0.50)",
  icon: "#737373",
  iconText: "#A3A3A3",
};

const LANGS = [
  { name: "TypeScript", slug: "typescript", color: "#3178c6" },
  { name: "Rust", slug: "rust", color: "#f67727" },
  { name: "Zig", slug: "zig", color: "#f7a41d" },
  { name: "Go", slug: "go", color: "#00ADD8" },
  { name: "Python", slug: "python", color: "#ffd83d" },
  { name: "Haskell", slug: "haskell", color: "#734cdd" },
  { name: "Clojure", slug: "clojure", color: "#50bb08" },
];

const TASK_META = [
  { slug: "primes", label: "Primes", icon: "code" },
  { slug: "http-rest", label: "Http", icon: "globe" },
  { slug: "json-parser", label: "JSON parser", icon: "json" },
  { slug: "word-frequency", label: "Word-freq", icon: "bars" },
];

const layout = {
  titleY: 52,
  subtitleY: 112,
  legendY: 178,

  iconX: 80,
  groupLabelX: 118,
  leftDividerX: 360,
  panelDividerX: 1045,

  groupTop: 240,
  rowGap: 24,
  groupGap: 52,

  barH: 12,
  barHWinner: 14,
};

// Canvas height adapts to LANGS.length so each task group fits its rows
// without overflowing into the next group. Scales cleanly to ~10 langs.
const groupRowsHeight = (LANGS.length - 1) * layout.rowGap;
const chartHeight = TASK_META.length * groupRowsHeight + (TASK_META.length - 1) * layout.groupGap;
const axisY = layout.groupTop + chartHeight + 100;

const W = 1672;
const H = axisY + 100;

const canvas = createCanvas(W, H);
const ctx = canvas.getContext("2d");

// `max` includes headroom past the worst value so the right-side label
// has room before the panel divider / canvas edge.
const TOKENS_AXIS = {
  leftX: 390,
  rightX: 960,
  max: 1400,
  ticks: [0, 200, 400, 600, 800, 1000, 1200, 1400],
  tickFmt: String,
  labelFmt: String,
  title: "Tokens",
};

const PPL_AXIS = {
  leftX: 1080,
  rightX: 1580,
  max: 3.0,
  ticks: [0, 0.5, 1, 1.5, 2, 2.5, 3],
  tickFmt: v => v.toFixed(1),
  labelFmt: v => v.toFixed(2),
  title: "Perplexity (ppl)",
};

const axisToX = (value, axis) => axis.leftX + (value / axis.max) * (axis.rightX - axis.leftX);

function font(weight, size, style = "normal") {
  return `${style} ${weight} ${size}px "Inter Display", "Noto Sans Display", "Aptos Display", "Arial Narrow", ui-sans-serif, system-ui, sans-serif`;
}

function roundedRect(x, y, w, h, r) {
  if (r === 0) {
    ctx.beginPath();
    ctx.rect(x, y, w, h);
    return;
  }
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

function line(x1, y1, x2, y2) {
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
}

function hexToRgb(hex) {
  const num = Number.parseInt(hex.slice(1), 16);
  return {
    r: (num >>> 16) & 255,
    g: (num >>> 8) & 255,
    b: (num >>> 0) & 255,
  };
}

function hueOf(rgb) {
  const r = rgb.r / 255, g = rgb.g / 255, b = rgb.b / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  if (max === min) return 0;

  let h;
  const d = max - min;
  if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;

  return h * 60;
}

function shiftHue(rgb, deltaDeg) {
  const r = rgb.r / 255, g = rgb.g / 255, b = rgb.b / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  let h = 0, s = 0;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h /= 6;
  }

  h = (h + deltaDeg / 360 + 1) % 1;

  const hue2rgb = (p, q, t) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };

  let r2 = l, g2 = l, b2 = l;
  if (s !== 0) {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r2 = hue2rgb(p, q, h + 1 / 3);
    g2 = hue2rgb(p, q, h);
    b2 = hue2rgb(p, q, h - 1 / 3);
  }

  return {
    r: Math.round(r2 * 255),
    g: Math.round(g2 * 255),
    b: Math.round(b2 * 255),
  };
}

function rgbToCss({ r, g, b }) {
  return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
}

function mix(a, b, t) {
  return {
    r: a.r * (1 - t) + b.r * t,
    g: a.g * (1 - t) + b.g * t,
    b: a.b * (1 - t) + b.b * t,
  };
}

function lighten(rgb, amount) {
  return Math.min(mix(rgb, { r: 255, g: 255, b: 255 }, amount), 255);
}

function saturate(rgb, amount) {
  const gray = 0.2126 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b;
  return {
    r: Math.max(Math.min(gray + (rgb.r - gray) * amount, 255), 0),
    g: Math.max(Math.min(gray + (rgb.g - gray) * amount, 255), 0),
    b: Math.max(Math.min(gray + (rgb.b - gray) * amount, 255), 0),
  };
}

function drawBar(x, y, w, h, color, radius = 3, gradient = true, glow = false) {
  if (w <= 0) return;
  ctx.save();

  // Stacked-blur outer glow. Each pass increases blur radius and drops
  // alpha geometrically (~0.6x per step), so the perceived falloff is
  // closer to exponential than a single shadowBlur gaussian. Outermost
  // pass has a large radius but contributes very little intensity.
  if (glow) {
    // Hue-shift the halo, opposite directions for warm vs cool colors:
    // warm hues (red / orange / yellow / green, hue 0..180) shift leftward;
    // cool hues (cyan / blue / purple, hue 180..360) shift rightward.
    const baseRgb = hexToRgb(color);
    const delta = hueOf(baseRgb) < 180 ? -25 : 15;
    const base = shiftHue(baseRgb, delta);
    const intensity = 1.0;

    const passes = [
      { blur: 6, alpha: 0.98 },
      { blur: 12, alpha: 0.62 },
      { blur: 36, alpha: 0.40 },
      { blur: 70, alpha: 0.16 },
      { blur: 140, alpha: 0.07 },
    ];

    for (const p of passes) {
      ctx.shadowBlur = p.blur;
      ctx.shadowColor = `rgba(${base.r}, ${base.g}, ${base.b}, ${p.alpha * intensity})`;
      ctx.fillStyle = color;
      roundedRect(x, y, w, h, radius);
      ctx.fill();
    }

    ctx.shadowBlur = 0;
  }

  if (!gradient) {
    // Winner bars (glow=true) render 7% lighter than the raw lang color
    // so the bar reads as the "hot" focal point on top of the halo.
    ctx.fillStyle = glow ? rgbToCss(lighten(hexToRgb(color), 0.07)) : color;
    roundedRect(x, y, w, h, radius);
    ctx.fill();
    ctx.restore();
    return;
  }

  const base = hexToRgb(color);
  const bg = hexToRgb(theme.bg);
  const start = saturate(mix(bg, base, 0.12), 1.22);
  const mid = saturate(mix(bg, base, 0.72), 1.12);

  const grad = ctx.createLinearGradient(x, 0, x + w, 0);
  grad.addColorStop(0.00, rgbToCss(start));
  grad.addColorStop(0.58, rgbToCss(mid));
  grad.addColorStop(1.00, color);

  ctx.fillStyle = grad;
  roundedRect(x, y, w, h, radius);
  ctx.fill();

  ctx.restore();
}

function drawBackground() {
  ctx.fillStyle = theme.bg;
  ctx.fillRect(0, 0, W, H);
}

function drawHeader() {
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  ctx.fillStyle = theme.text;
  ctx.font = font(800, 44);
  ctx.fillText("LLM Code Benchmark: tokens and perplexity", W / 2, layout.titleY);

  ctx.fillStyle = theme.muted;
  ctx.font = font(400, 26);
  ctx.fillText("Both metrics: lower is better", W / 2, layout.subtitleY);

  ctx.font = font(500, 23);
  const widths = LANGS.map(l => 38 + 14 + ctx.measureText(l.name).width + 40);
  const total = widths.reduce((a, b) => a + b, 0) - 40;
  let x = (W - total) / 2;

  for (let i = 0; i < LANGS.length; i++) {
    drawBar(x, layout.legendY - 8, 38, 16, LANGS[i].color, 8, false);

    ctx.fillStyle = theme.text;
    ctx.textAlign = "left";
    ctx.font = font(500, 23);
    ctx.fillText(LANGS[i].name, x + 52, layout.legendY);

    x += widths[i];
  }
}

function dashedLine(x1, y1, x2, y2, dash = 5, gap = 9) {
  const dx = x2 - x1, dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  const ux = dx / len, uy = dy / len;
  ctx.beginPath();
  for (let d = 0; d < len; d += dash + gap) {
    const end = Math.min(d + dash, len);
    ctx.moveTo(x1 + ux * d, y1 + uy * d);
    ctx.lineTo(x1 + ux * end, y1 + uy * end);
  }
  ctx.stroke();
}

function drawVerticalPanelLabel(x, y, text) {
  ctx.save();

  ctx.translate(x, y);
  ctx.rotate(-Math.PI / 2);

  ctx.font = font(400, 27, "italic");
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "rgba(255, 255, 255, 0.7)";
  ctx.fillText(text, 0, 0);

  ctx.restore();
}

function drawAxesAndGrid() {
  const top = layout.groupTop - 32;
  const bottom = axisY - 40;
  const chartMidY = (top + bottom) / 2;

  ctx.strokeStyle = theme.divider;
  ctx.lineWidth = 2;
  line(layout.leftDividerX, top - 4, layout.leftDividerX, bottom + 18);
  line(layout.panelDividerX, top - 4, layout.panelDividerX, bottom + 18);

  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.font = font(400, 21);
  ctx.fillStyle = theme.muted;

  for (const axis of [TOKENS_AXIS, PPL_AXIS]) {
    for (const tick of axis.ticks) {
      const x = axisToX(tick, axis);
      if (tick !== 0) {
        ctx.strokeStyle = theme.grid;
        ctx.lineWidth = 1;
        dashedLine(x, top + 8, x, bottom);
      }
      ctx.fillText(axis.tickFmt(tick), x, axisY + 14);
    }
  }

  drawVerticalPanelLabel(layout.leftDividerX - 32, chartMidY, TOKENS_AXIS.title);
  drawVerticalPanelLabel(layout.panelDividerX - 32, chartMidY, PPL_AXIS.title);
}

function drawIcon(cx, cy, type) {
  ctx.save();

  ctx.strokeStyle = theme.icon;
  ctx.fillStyle = theme.icon;
  ctx.lineWidth = 4;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  if (type === "code") {
    line(cx - 10, cy - 9, cx - 22, cy);
    line(cx - 22, cy, cx - 10, cy + 9);
    line(cx + 10, cy - 9, cx + 22, cy);
    line(cx + 22, cy, cx + 10, cy + 9);
    line(cx + 4, cy - 17, cx - 4, cy + 17);
  }

  if (type === "globe") {
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(cx, cy, 21, 0, Math.PI * 2);
    ctx.stroke();

    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.ellipse(cx, cy, 8, 21, 0, 0, Math.PI * 2);
    ctx.stroke();

    ctx.beginPath();
    ctx.ellipse(cx, cy - 5, 19, 8, 0, 0, Math.PI * 2);
    ctx.stroke();

    ctx.beginPath();
    ctx.ellipse(cx, cy + 5, 19, 8, 0, 0, Math.PI * 2);
    ctx.stroke();
  }

  if (type === "json") {
    ctx.font = font(700, 33);
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("{ }", cx, cy - 1);
  }

  if (type === "bars") {
    ctx.lineWidth = 3;
    const baseY = cy + 16;
    const xs = [cx - 18, cx - 4, cx + 10];
    const hs = [17, 29, 41];
    for (let i = 0; i < 3; i++) {
      roundedRect(xs[i], baseY - hs[i], 8, hs[i], 1);
      ctx.stroke();
    }
  }

  ctx.restore();
}

const minByValue = (obj) => Object.keys(obj).reduce((a, b) => obj[a] < obj[b] ? a : b);

function drawMetric(axis, value, isWinner, color, y) {
  const h = isWinner ? layout.barHWinner : layout.barH;
  const w = axisToX(value, axis) - axis.leftX;
  drawBar(axis.leftX + 1, y - h / 2, w, h, color, h / 2, !isWinner, isWinner);
  ctx.fillStyle = isWinner ? theme.text : "#e1e5ec";
  ctx.font = isWinner ? font(700, 19) : font(400, 17);
  ctx.textAlign = "left";
  ctx.fillText(axis.labelFmt(value), axis.leftX + w + 13, y);
}

function drawBars(tasks) {
  ctx.textBaseline = "middle";

  tasks.forEach((task, gi) => {
    const groupRowsHeight = (LANGS.length - 1) * layout.rowGap;
    const groupY = layout.groupTop + gi * (groupRowsHeight + layout.groupGap);
    const centerY = groupY + groupRowsHeight / 2;

    drawIcon(layout.iconX, centerY, task.icon);

    ctx.textAlign = "left";
    ctx.fillStyle = theme.iconText;
    ctx.font = font(600, 22);
    ctx.fillText(task.label, layout.groupLabelX, centerY);

    const tokWinner = minByValue(task.tokens);
    const pplWinner = minByValue(task.ppl);

    LANGS.forEach((lang, li) => {
      const y = groupY + li * layout.rowGap;
      drawMetric(TOKENS_AXIS, task.tokens[lang.name], lang.name === tokWinner, lang.color, y);
      drawMetric(PPL_AXIS, task.ppl[lang.name], lang.name === pplWinner, lang.color, y);
    });
  });
}

async function loadTasks() {
  const [tok, perp] = await Promise.all([
    readFile(resolve(RESULTS_DIR, "tokens.json"), "utf-8").then(JSON.parse),
    readFile(resolve(RESULTS_DIR, "perplexity.json"), "utf-8").then(JSON.parse),
  ]);
  return TASK_META.map(meta => {
    const tokRow = tok.examples.find(e => e.task === meta.slug);
    const tokens = {}, ppl = {};
    for (const lang of LANGS) {
      tokens[lang.name] = tokRow[lang.slug];
      ppl[lang.name] = perp.results.find(r => r.task === meta.slug && r.lang === lang.slug).ppl;
    }
    return { ...meta, tokens, ppl };
  });
}

async function main() {
  const tasks = await loadTasks();
  drawBackground();
  drawHeader();
  drawAxesAndGrid();
  drawBars(tasks);
  const buf = canvas.toBuffer("image/png");
  await writeFile(OUT_PATH, buf);
  console.log(`wrote ${OUT_PATH}`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
