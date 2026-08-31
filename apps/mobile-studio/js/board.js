/** 칠판 Canvas 렌더러 — 필기·그래프 */

const COLORS = {
  bg: "#1a3d32",
  frame: "#6a8a78",
  white: "#ece8dc",
  yellow: "#f5e6a8",
  pink: "#f0b8c8",
  cyan: "#a8dce8",
  faint: "#6a8a78",
  green: "#83c167",
};

const GRAPH_FNS = {
  f_prime: (x) => -6 * (x + 1) * (x - 1),
  parabola: (x) => x * x - 2,
  cubic: (x) => -0.3 * (x + 1) * (x - 1) * (x - 2),
};

export class ChalkCanvas {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.w = canvas.width;
    this.h = canvas.height;
    this.mathLines = [];
    this.graphState = null;
    this.dots = [];
    this.caption = "";
    this.header = { brand: "", title: "" };
    this._katexCache = new Map();
  }

  clear() {
    this.mathLines = [];
    this.graphState = null;
    this.dots = [];
    this.caption = "";
    this.drawFrame();
  }

  setHeader(brand, title) {
    this.header = { brand, title };
  }

  drawFrame() {
    const { ctx, w, h } = this;
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, w, h);

    // chalk dust
    ctx.fillStyle = "rgba(106,138,120,0.15)";
    for (let i = 0; i < 80; i++) {
      const x = ((i * 97) % w);
      const y = ((i * 53) % h);
      ctx.beginPath();
      ctx.arc(x, y, 1.2, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.strokeStyle = COLORS.frame;
    ctx.lineWidth = 3;
    ctx.strokeRect(16, 16, w - 32, h - 32);

    ctx.fillStyle = COLORS.faint;
    ctx.font = "18px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(this.header.brand || "", 28, 44);
    ctx.fillStyle = COLORS.yellow;
    ctx.font = "bold 26px sans-serif";
    ctx.fillText(this.header.title || "", 28, 76);

    this._drawGraphArea();
    this._drawMathStack();
    this._drawCaption();
  }

  _graphRect() {
    return { x: 28, y: 100, w: this.w * 0.52 - 28, h: this.h * 0.55 };
  }

  _mathRect() {
    return { x: this.w * 0.52, y: 100, w: this.w * 0.48 - 28, h: this.h * 0.55 };
  }

  _dataToCanvas(g, x, y) {
    const xr = g.xRange;
    const yr = g.yRange;
    const px = g.rect.x + ((x - xr[0]) / (xr[1] - xr[0])) * g.rect.w;
    const py = g.rect.y + g.rect.h - ((y - yr[0]) / (yr[1] - yr[0])) * g.rect.h;
    return { px, py };
  }

  _drawGraphArea() {
    const g = this.graphState;
    if (!g) return;
    const { ctx } = this;
    const rect = g.rect;

    // axes
    ctx.strokeStyle = COLORS.faint;
    ctx.lineWidth = 1.5;
    const origin = this._dataToCanvas(g, 0, 0);
    ctx.beginPath();
    ctx.moveTo(rect.x, origin.py);
    ctx.lineTo(rect.x + rect.w, origin.py);
    ctx.moveTo(origin.px, rect.y);
    ctx.lineTo(origin.px, rect.y + rect.h);
    ctx.stroke();

    // curve progress
    if (g.progress > 0 && g.fn) {
      ctx.strokeStyle = COLORS.yellow;
      ctx.lineWidth = 3;
      ctx.beginPath();
      const n = Math.floor(120 * g.progress);
      for (let i = 0; i <= n; i++) {
        const t = i / 120;
        const x = g.xRange[0] + t * (g.xRange[1] - g.xRange[0]);
        const y = g.fn(x);
        const { px, py } = this._dataToCanvas(g, x, y);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();
    }

    if (g.title && g.progress >= 1) {
      ctx.fillStyle = COLORS.yellow;
      ctx.font = "16px sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(g.title, rect.x, rect.y - 6);
    }

    // dots
    for (const d of this.dots) {
      if (!d.visible) continue;
      const { px, py } = this._dataToCanvas(g, d.x, d.y);
      const col = d.color === "pink" ? COLORS.pink : COLORS.yellow;
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.arc(px, py, 7, 0, Math.PI * 2);
      ctx.fill();
      if (d.label) {
        ctx.fillStyle = col;
        ctx.font = "14px sans-serif";
        ctx.fillText(d.label, px + 10, py - 8);
      }
    }
  }

  async _renderKatex(latex, maxWidth) {
    if (this._katexCache.has(latex)) return this._katexCache.get(latex);
    if (typeof katex === "undefined") return null;
    try {
      const html = katex.renderToString(latex, { throwOnError: false, displayMode: false });
      const div = document.createElement("div");
      div.style.cssText = "position:fixed;left:-9999px;background:transparent;color:#ece8dc;font-size:22px;padding:4px;";
      div.innerHTML = html;
      document.body.appendChild(div);
      const scale = Math.min(1, maxWidth / div.offsetWidth);
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${div.offsetWidth * scale}" height="${div.offsetHeight * scale}">
        <foreignObject width="100%" height="100%">
          <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:${22 * scale}px;color:#ece8dc;">${html}</div>
        </foreignObject></svg>`;
      document.body.removeChild(div);
      const img = await new Promise((res, rej) => {
        const i = new Image();
        i.onload = () => res(i);
        i.onerror = rej;
        i.src = "data:image/svg+xml," + encodeURIComponent(svg);
      });
      this._katexCache.set(latex, img);
      return img;
    } catch {
      return null;
    }
  }

  _drawMathStack() {
    const { ctx, mathLines } = this;
    const rect = this._mathRect();
    let y = rect.y + 10;
    for (const line of mathLines) {
      const alpha = line.faded ? 0.45 : 1;
      ctx.globalAlpha = alpha;
      if (line.img) {
        ctx.drawImage(line.img, rect.x, y, line.img.width, line.img.height);
        y += line.img.height + 8;
      } else if (line.text) {
        ctx.fillStyle = line.color || COLORS.white;
        ctx.font = `${line.faded ? "18" : "22"}px sans-serif`;
        ctx.textAlign = "left";
        const maxW = rect.w;
        wrapText(ctx, line.text, rect.x, y + 18, maxW, 24);
        y += 36;
      }
      ctx.globalAlpha = 1;
      if (line.showArrow && !line.faded) {
        ctx.fillStyle = COLORS.faint;
        ctx.font = "16px sans-serif";
        ctx.fillText("⇓", rect.x, y);
        y += 20;
      }
    }
  }

  _drawCaption() {
    if (!this.caption) return;
    const { ctx, w, h } = this;
    ctx.fillStyle = COLORS.cyan;
    ctx.font = "20px sans-serif";
    ctx.textAlign = "center";
    const text = this.caption;
    const maxW = w - 48;
    wrapText(ctx, text, w / 2, h - 72, maxW, 26, true);
  }

  setCaption(text) {
    this.caption = text;
    this.drawFrame();
  }

  fadeMathLines() {
    for (const l of this.mathLines) l.faded = true;
  }

  async addMathLine(latex, { faded = false } = {}) {
    this.fadeMathLines();
    const rect = this._mathRect();
    const img = await this._renderKatex(latex, rect.w - 8);
    const entry = { latex, img, faded: false, showArrow: this.mathLines.length > 0 };
    if (!img) entry.text = latex;
    this.mathLines.push(entry);
    this.drawFrame();
    return entry;
  }

  /** typewriter caption on board */
  async animateCaption(fullText, msPerChar = 40) {
    for (let i = 1; i <= fullText.length; i++) {
      this.caption = fullText.slice(0, i);
      this.drawFrame();
      await sleep(msPerChar);
    }
  }

  setGraph(graphType, title, progress = 1) {
    const fn = GRAPH_FNS[graphType] || GRAPH_FNS.f_prime;
    let xRange = [-2.5, 2.5];
    let yRange = [-2, 8];
    if (graphType === "parabola") yRange = [-3, 6];
    if (graphType === "cubic") {
      xRange = [-2, 3];
      yRange = [-4, 6];
    }
    this.graphState = {
      fn,
      graphType,
      title: title || "",
      xRange,
      yRange,
      rect: this._graphRect(),
      progress,
    };
    this.drawFrame();
  }

  async animateGraph(graphType, title, durationMs = 1200) {
    this.setGraph(graphType, title, 0);
    const steps = 30;
    const dt = durationMs / steps;
    for (let s = 1; s <= steps; s++) {
      this.graphState.progress = s / steps;
      this.drawFrame();
      await sleep(dt);
    }
  }

  addDot(x, y, label = "", color = "yellow") {
    this.dots.push({ x, y, label, color, visible: true });
    this.drawFrame();
  }

  async animateDot(x, y, label, color) {
    const d = { x, y, label, color, visible: false };
    this.dots.push(d);
    for (let r = 0; r <= 7; r++) {
      d._r = r;
      d.visible = true;
      this.drawFrame();
      // pulse ring
      if (this.graphState) {
        const { ctx } = this;
        const { px, py } = this._dataToCanvas(this.graphState, x, y);
        ctx.strokeStyle = color === "pink" ? COLORS.pink : COLORS.yellow;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(px, py, r * 2, 0, Math.PI * 2);
        ctx.stroke();
      }
      await sleep(35);
    }
    this.drawFrame();
  }
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight, center = false) {
  const words = text.split("");
  let line = "";
  const lines = [];
  for (const ch of words) {
    const test = line + ch;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = ch;
    } else line = test;
  }
  lines.push(line);
  lines.forEach((ln, i) => {
    if (center) ctx.textAlign = "center";
    ctx.fillText(ln, x, y + i * lineHeight);
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

export { COLORS, sleep };
