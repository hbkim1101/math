/* Explainer Studio – 무대(스테이지): 렌더 없이 브라우저에서 장면을 바로 그려 보는 즉시 미리보기.
 *
 *  simulate(doc, segIdx)          장면 0..segIdx 의 동작을 순서대로 적용해 칠판 상태(칸별 판서·그래프·말풍선)를 만든다
 *  render(container, doc, opts)   16:9 무대(1280×720 논리 좌표)를 DOM+SVG 로 그린다. opts.cursor 의 동작은 노란 테두리
 *  thumbnail(doc, segIdx, width)  장면 끝 상태의 축소판 (장면 목록용, HTML 문자열 캐시)
 *
 *  실제 Manim 렌더와 픽셀이 같지는 않다 — "무엇이 어디에 놓이는지" 를 편집 즉시 보여 주는 안내용이다. */
window.StudioStage = (() => {
  "use strict";
  const W = 1280, H = 720;                   // 논리 크기 (16:9)
  const UNIT = W / 14.2;                     // Manim 단위(섹션 폭 14.2) → px
  const el = (tag, attrs = {}, ...kids) => {
    const n = tag.startsWith("svg:") ? document.createElementNS("http://www.w3.org/2000/svg", tag.slice(4)) : document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === undefined || v === null || v === false) continue;
      if (k === "class") n.setAttribute("class", v);
      else if (k === "style") n.setAttribute("style", v);
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? "" : v);
    }
    for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) n.append(c.nodeType ? c : document.createTextNode(String(c)));
    return n;
  };
  const COLOR_HEX = { chalk: "#f2f2e6", accent: "#ffd23f", highlight: "#ff9f43", exp: "#7cc4ff", log: "#ff7ab6", q1: "#5ad48a", q2: "#b48cff",
    point: "#ffd23f", rect: "#4fd1c5", axis_sym: "#c9c9c9", guide: "#a9b4a9", ok: "#5ad48a", warn: "#ff9f43", muted: "#9aa39a", text: "#f2f2e6",
    red: "#ff6b6b", blue: "#7cc4ff", green: "#5ad48a", yellow: "#ffd23f", orange: "#ff9f43", purple: "#b48cff", pink: "#ff7ab6", white: "#f2f2e6", teal: "#4fd1c5" };
  const colorOf = (doc, name, fallback = "#f2f2e6") => {
    if (!name) return fallback;
    const c = (doc.colors || {})[name] ?? name;
    if (/^#|^rgb/.test(c)) return c;
    return COLOR_HEX[c] || COLOR_HEX[name] || fallback;
  };

  // ------------------------------------------------------------------ 수식 조판 (KaTeX 있으면)
  const stripTex = (s) => String(s ?? "").replace(/\\(tfrac|dfrac|frac)\{([^}]*)\}\{([^}]*)\}/g, "$2/$3").replace(/\\(left|right|Bigl|Bigr|bigl|bigr)\b/g, "")
    .replace(/\\(quad|qquad|;|,|!)/g, " ").replace(/\\(Rightarrow|to)/g, "→").replace(/\\(times|cdot)/g, "×").replace(/\\[a-zA-Z]+/g, (m) => m.slice(1)).replace(/[{}$]/g, "").trim();
  function math(str, { onlyMath = false } = {}) {
    const span = el("span", { class: "st-math" });
    const s = String(str ?? "");
    if (typeof window.katex === "undefined") { span.textContent = stripTex(s); return span; }
    const put = (node, tex) => { try { window.katex.render(tex, node, { throwOnError: false, strict: "ignore", trust: true }); } catch (_) { node.textContent = stripTex(tex); } };
    if (onlyMath && !s.includes("$")) { put(span, s); return span; }
    for (const p of s.split(/(\$[^$]*\$)/g)) {
      if (!p) continue;
      if (p.startsWith("$") && p.endsWith("$") && p.length > 1) { const m = el("span"); put(m, p.slice(1, -1)); span.append(m); }
      else span.append(el("span", { class: "st-txt" }, p));
    }
    return span;
  }

  // ------------------------------------------------------------------ 파이썬식 수식 → JS 함수 (그래프용)
  function pyToJs(src) {
    let s = String(src).trim();
    // A if C else B  →  ((C) ? (A) : (B))   (왼쪽부터, 괄호 깊이 0 에서만)
    const conv = (t) => {
      const i = findTop(t, " if ");
      if (i < 0) return t;
      const A = t.slice(0, i), rest = t.slice(i + 4);
      const j = findTop(rest, " else ");
      if (j < 0) return t;
      return `((${conv(rest.slice(0, j))}) ? (${conv(A)}) : (${conv(rest.slice(j + 6))}))`;
    };
    s = conv(s);
    s = s.replace(/\band\b/g, "&&").replace(/\bor\b/g, "||").replace(/\bnot\b/g, "!");
    return s;
  }
  function findTop(t, needle) {
    let depth = 0;
    for (let i = 0; i < t.length; i++) {
      const c = t[i];
      if (c === "(" || c === "[") depth++; else if (c === ")" || c === "]") depth--;
      else if (depth === 0 && t.startsWith(needle, i)) return i;
    }
    return -1;
  }
  const MATH_PRELUDE = "const {exp,log,sin,cos,tan,sqrt,abs,PI,E,pow,atan,asin,acos,sinh,cosh,tanh,floor,ceil,min,max,sign}=Math; const pi=PI,e=E,ln=log,log2=Math.log2,log10=Math.log10;";
  function makeEnv(doc) {
    const consts = {};
    for (const [k, v] of Object.entries(doc.params || {})) {
      if (typeof v === "number") { consts[k] = v; continue; }
      try { consts[k] = new Function(...Object.keys(consts), `${MATH_PRELUDE} return (${pyToJs(v)});`)(...Object.values(consts)); }
      catch (_) { consts[k] = NaN; }
    }
    const names = Object.keys(consts), vals = Object.values(consts);
    const num = (v) => {
      if (typeof v === "number") return v;
      if (typeof v !== "string") return NaN;
      if (consts[v] !== undefined) return consts[v];
      try { const r = new Function(...names, `${MATH_PRELUDE} return (${pyToJs(v)});`)(...vals); return typeof r === "number" ? r : NaN; } catch (_) { return NaN; }
    };
    const fn = (expr) => {
      try { const f = new Function("x", ...names, `${MATH_PRELUDE} return (${pyToJs(expr)});`); const t = f(0.37, ...vals); if (typeof t !== "number" && typeof t !== "boolean") return null; return (x) => f(x, ...vals); }
      catch (_) { return null; }
    };
    return { num, fn, consts };
  }

  // ------------------------------------------------------------------ 시뮬레이션
  const DIR = { UP: [0, -1], DOWN: [0, 1], LEFT: [-1, 0], RIGHT: [1, 0], UL: [-1, -1], UR: [1, -1], DL: [-1, 1], DR: [1, 1] };
  function newSection(s) { return { id: s.id, title: s.title || "", layout: s.layout || "full", graph_width: s.graph_width, items: [], graph: null, caption: null, banner: null }; }

  /** 장면 0..segIdx 를 적용한 상태. 각 요소에 meta={seg,act,id} 를 남겨 렌더러가 편집 중 요소를 알 수 있게 한다. */
  function simulate(doc, segIdx) {
    const style = (doc.meta || {}).style || "panel";
    const chalk = ((doc.layout || {}).chalk) || {};
    const graphLay = ((doc.layout || {}).graph) || {};
    const env = makeEnv(doc);
    const secs = {}; const order = [];
    const secList = style === "chalkboard" && Array.isArray(chalk.sections) && chalk.sections.length ? chalk.sections : [{ id: "board", title: style === "panel" ? (((doc.layout || {}).board || {}).title || "풀이") : "", layout: "split" }];
    for (const s of secList) { if (s && s.id) { secs[s.id] = newSection(s); order.push(s.id); } }
    const M = { style, secs, order, current: order[0], hidden: new Set(), dim: new Map(), points: {}, env, chalk, graphLay, warn: [] };
    const cur = () => secs[M.current] || (secs[order[0]]);
    const graph = () => { const s = cur(); if (!s.graph) s.graph = defaultGraph(); return s.graph; };
    const defaultGraph = () => ({ xr: (graphLay.x_range || [-4, 4, 1]).map(env.num), yr: (graphLay.y_range || [-3, 3, 1]).map(env.num), elems: [], numbers: graphLay.numbers !== false, equal: true });
    const pt = (v) => (Array.isArray(v) ? v.map(env.num) : typeof v === "string" && M.points[v] ? M.points[v] : null);
    const findDerive = (id) => { for (const sid of order) { const it = secs[sid].items.find((x) => x.kind === "derive" && x.id === id); if (it) return it; } return null; };
    const findProblem = () => { for (const sid of order) { const it = secs[sid].items.find((x) => x.kind === "problem"); if (it) return it; } return null; };

    const segs = doc.segments || [];
    for (let si = 0; si <= Math.min(segIdx, segs.length - 1); si++) {
      const acts = (segs[si] || {}).actions || [];
      acts.forEach((a, ai) => {
        if (!a || typeof a !== "object") return;
        const meta = { seg: si, act: ai, id: a.id, do: a.do };
        const s = cur();
        switch (a.do) {
          case "goto": if (secs[a.section]) M.current = a.section; else M.warn.push({ meta, msg: `없는 칸 ${a.section}` }); break;
          case "section": s.banner = { text: a.text, meta }; break;
          case "title_card": s.items.push({ kind: "title", title: a.title, subtitle: a.subtitle, tag: a.tag, meta }); break;
          case "end_card": s.items.push({ kind: "end", title: a.title, lines: a.lines || [], meta }); break;
          case "problem": s.items.push({ kind: "problem", title: a.title, lines: a.lines || (a.tex ? [a.tex] : []), choices: a.choices || null, focus: null, docked: false, meta,
            style: a.image ? "image" : (a.style || "paper"), image: a.image || null }); break;
          case "problem_focus": { const p = findProblem(); if (p) p.focus = a.index ?? 0; break; }
          case "problem_dock": { const p = findProblem(); if (p) { p.docked = true; p.focus = null; } break; }
          case "answer": {
            const p = findProblem(); if (a.choice && p) p.answer = { choice: a.choice, meta };
            if (a.tex) s.items.push({ kind: "line", tex: a.tex, box: true, color: "accent", meta, id: a.id || "answer" });
            if (a.caption_text) s.caption = { text: a.caption_text, meta };
            break;
          }
          case "write": case "board_write": {
            const lines = a.lines || (a.tex !== undefined ? [a.tex] : a.text !== undefined ? [a.text] : []);
            if (a.space) s.items.push({ kind: "space", dy: Number(a.space), meta });
            lines.forEach((t, k) => s.items.push({ kind: "line", tex: t, plain: !!a.plain, ko: !!a.ko, color: a.color, box: !!a.box, underline: !!a.underline, indent: Number(a.indent || 0), scale: a.scale, meta, id: k === 0 ? a.id : undefined }));
            break;
          }
          case "board_replace": { const ls = s.items.filter((x) => x.kind === "line"); const t = ls[a.index < 0 ? ls.length + a.index : a.index]; if (t) { t.tex = a.tex; t.meta = meta; } break; }
          case "board_title": s.title = a.text; break;
          case "board_clear": s.items = s.items.filter((x) => x.kind !== "line" && x.kind !== "derive"); break;
          case "board_highlight": { const ls = s.items.filter((x) => x.kind === "line"); const t = ls[a.index < 0 ? ls.length + a.index : a.index]; if (t) t.hl = meta; break; }
          case "space": s.items.push({ kind: "space", dy: Number(a.dy ?? 0.3), meta }); break;
          case "derive": s.items.push({ kind: "derive", id: a.id || "d", color: a.color, scale: a.scale, indent: Number(a.indent || 0), steps: (a.steps || []).map((st) => ({ ...st, meta })), meta }); break;
          case "step": { const d = findDerive(a.of || "d"); const st = { ...a, meta }; delete st.do; delete st.of; if (d) d.steps.push(st); else s.items.push({ kind: "derive", id: a.of || "d", steps: [st], meta }); break; }
          case "caption": s.caption = a.text || a.tex ? { text: a.text ?? a.tex, meta } : null; break;
          case "axes": { const g = graph(); if (a.x_range) g.xr = a.x_range.map(env.num); if (a.y_range) g.yr = a.y_range.map(env.num); g.numbers = a.numbers !== false; g.equal = a.equal_aspect !== false; g.meta = meta; g.labels = a.labels !== false; break; }
          case "plot": case "line": case "vline": case "segment": case "arrow": case "polygon": case "guides": {
            const g = graph(); const e = { kind: a.do, id: a.id, color: a.color, dashed: !!a.dashed, label: a.label, label_at: a.label_at, label_dir: a.label_dir, meta, stroke: a.stroke_width };
            if (a.do === "plot") { e.f = env.fn(a.expr); e.expr = a.expr; e.xr = a.x_range ? a.x_range.map(env.num) : null; }
            if (a.do === "line") { if (a.expr) e.f = env.fn(a.expr); else if (a.through) { const p1 = pt(a.through[0]), p2 = pt(a.through[1]); if (p1 && p2) { const m = (p2[1] - p1[1]) / (p2[0] - p1[0]); e.f = (x) => p1[1] + m * (x - p1[0]); } } else { const m = env.num(a.slope ?? 1), b = env.num(a.intercept ?? 0); e.f = (x) => m * x + b; } e.xr = a.x_range ? a.x_range.map(env.num) : null; }
            if (a.do === "vline") e.x = env.num(a.x);
            if (a.do === "segment" || a.do === "arrow") { e.a = pt(a.a); e.b = pt(a.b); }
            if (a.do === "polygon") e.pts = (a.points || []).map(pt).filter(Boolean); e.fill = a.fill_opacity;
            if (a.do === "guides") { e.p = pt(a.point); e.xl = a.x_label; e.yl = a.y_label; }
            g.elems.push(e); break;
          }
          case "point": { const g = graph(); const p = pt(a.pos ?? a.at); if (p) { if (a.id) M.points[a.id] = p; g.elems.push({ kind: "point", id: a.id, p, color: a.color, label: a.label ?? a.id, label_dir: a.label_dir, meta }); } break; }
          case "points": { const g = graph(); (a.items || []).forEach((it) => { const p = pt(it.at ?? it.pos); if (p) { if (it.id) M.points[it.id] = p; g.elems.push({ kind: "point", id: it.id, p, color: it.color || a.color, label: it.label ?? it.id, label_dir: it.label_dir, meta }); } }); break; }
          case "reflect": { const g = graph(); const p = pt(a.source); const m = env.num(a.slope ?? 1), b = env.num(a.intercept ?? 0); if (p) { const d = (p[0] + (p[1] - b) * m) / (1 + m * m); const q = [2 * d - p[0], 2 * d * m - p[1] + 2 * b]; if (a.id) M.points[a.id] = q; g.elems.push({ kind: "point", id: a.id, p: q, color: a.color, label: a.label ?? a.id, label_dir: a.label_dir, meta, from: p, dashed: true }); } break; }
          case "translate_copy": { const g = graph(); const p = pt(a.source); if (p) { const q = [p[0] + env.num(a.dx ?? 0), p[1] + env.num(a.dy ?? 0)]; if (a.id) M.points[a.id] = q; g.elems.push({ kind: "point", id: a.id, p: q, color: a.color, label: a.label ?? a.id, label_dir: a.label_dir, meta, from: p, arrow: a.arrow !== false }); } break; }
          case "label": { const g = graph(); const p = pt(a.pos) || (a.near && M.points[a.near]) || null; g.elems.push({ kind: "label", id: a.id, p, text: a.tex, dir: a.dir, color: a.color, meta }); break; }
          case "custom": { const g = s.layout === "split" || style === "panel" ? graph() : null; const e = { kind: "custom", fn: a.fn, id: a.id, color: a.color, meta }; if (a.func && M.points) { e.f = env.fn(a.func); } if (g) g.elems.push(e); else s.items.push({ kind: "custom", fn: a.fn, meta }); break; }
          case "highlight": (Array.isArray(a.ids) ? a.ids : [a.ids]).forEach((id) => { M.hl = M.hl || []; M.hl.push({ id, meta, mode: a.mode }); }); break;
          case "dim": (Array.isArray(a.ids) ? a.ids : [a.ids]).forEach((id) => M.dim.set(id, a.opacity ?? 0.25)); break;
          case "undim": (Array.isArray(a.ids) ? a.ids : [a.ids]).forEach((id) => M.dim.delete(id)); break;
          case "fade": (Array.isArray(a.ids) ? a.ids : [a.ids]).forEach((id) => { if (a.out === false) M.hidden.delete(id); else M.hidden.add(id); }); break;
          case "clear": if (a.ids) (Array.isArray(a.ids) ? a.ids : [a.ids]).forEach((id) => M.hidden.add(id)); else { s.items = []; s.graph = null; s.caption = null; } break;
          case "camera": s.camera = { meta, reset: !!a.reset, sections: a.sections, focus: a.focus }; break;
          default: break;   // wait, board 등은 화면 변화 없음
        }
      });
    }
    return M;
  }

  // ------------------------------------------------------------------ 렌더
  const cmp = (meta, cursor) => (!cursor || cursor.act === null || cursor.act === undefined ? (meta.seg === cursor?.seg ? "curseg" : meta.seg < (cursor?.seg ?? Infinity) ? "past" : "future")
    : meta.seg < cursor.seg ? "past" : meta.seg > cursor.seg ? "future" : meta.act < cursor.act ? "curseg" : meta.act === cursor.act ? "editing" : "future");

  /** container 안에 무대를 그린다. opts: {cursor:{seg,act|null}, section?, subtitle?, onPick(seg,act), scale?} */
  function render(container, doc, opts = {}) {
    const cursor = opts.cursor || { seg: 0, act: null };
    const M = simulate(doc, cursor.seg);
    // 보여 줄 칸: 커서 동작 시점의 카메라 칸 (동작이 goto 면 목적지)
    let secId = opts.section || M.current;
    if (!opts.section && cursor.act !== null && cursor.act !== undefined) {
      const M2 = simulateUntil(doc, cursor);
      secId = M2.current;
    }
    const S = M.secs[secId] || M.secs[M.order[0]];
    const chalk = M.chalk; const boardColor = chalk.board_color || (M.style === "panel" ? "#111827" : "#24493a");
    const stage = el("div", { class: "stage", style: `width:${W}px;height:${H}px;background:${boardColor}` });
    const tag = (node, meta, label) => {
      if (!meta) return node;
      const rel = cmp(meta, cursor);
      node.classList.add("st-el", "st-" + rel);
      if (meta.id && M.hidden.has(meta.id)) node.classList.add("st-hidden");
      if (meta.id && M.dim.has(meta.id)) node.style.opacity = String(M.dim.get(meta.id));
      if ((M.hl || []).some((h) => h.id === meta.id && cmp(h.meta, cursor) === "editing")) node.classList.add("st-hl");
      node.dataset.seg = meta.seg; node.dataset.act = meta.act;
      node.title = `${label || meta.do} — ${meta.seg + 1}번째 장면 › ${meta.act + 1}번째 동작 (클릭: 카드 열기)`;
      node.addEventListener("click", (e) => { e.stopPropagation(); opts.onPick && opts.onPick(meta.seg, meta.act); });
      return node;
    };

    // 제목 (칠판 위)
    const margin = (chalk.margin ?? 0.55) * UNIT;
    let top = 26;
    if (S.title) { stage.append(el("div", { class: "st-title", style: `left:${margin}px;top:${top}px` }, S.title)); top += 70; } else top += 20;
    if (S.banner) stage.append(tag(el("div", { class: "st-banner" }, S.banner.text), S.banner.meta, "섹션 배너"));
    const bottomReserve = (chalk.bottom_reserve ?? 1.1) * UNIT;
    const bodyBottom = H - bottomReserve;
    const split = S.layout === "split";
    const gW = split ? ((S.graph_width ?? chalk.graph_width ?? 7.2) * UNIT) : 0;
    const colX = split ? margin + gW + 30 : margin + 10;
    const colW = W - colX - margin;

    // 그래프 영역 (split)
    if (split) {
      const box = { x: margin, y: top, w: gW, h: bodyBottom - top - 8 };
      stage.append(renderGraph(S.graph, box, M, doc, tag, cursor));
      if (S.caption) stage.append(tag(el("div", { class: "st-caption", style: `left:${box.x + 12}px;width:${box.w - 24}px;top:${box.y + box.h - 62}px` }, math(S.caption.text)), S.caption.meta, "설명 말풍선"));
    } else if (S.caption) {
      stage.append(tag(el("div", { class: "st-caption", style: `left:${margin + 60}px;width:${W - 2 * margin - 120}px;top:${bodyBottom - 62}px` }, math(S.caption.text)), S.caption.meta, "설명 말풍선"));
    }

    // 판서 열
    const col = el("div", { class: "st-col", style: `left:${colX}px;top:${top}px;width:${colW}px;height:${bodyBottom - top}px` });
    const base = 30 * ((chalk.line_scale ?? 0.72) / 0.72);
    for (const it of S.items) {
      if (it.kind === "space") { col.append(el("div", { style: `height:${it.dy * UNIT * 0.6}px` })); continue; }
      if (it.kind === "line") {
        const fs = base * (it.scale || 1);
        const node = el("div", { class: "st-line" + (it.box ? " box" : "") + (it.underline ? " ul" : "") + (it.plain || it.ko ? " ko" : ""), style: `font-size:${fs}px;margin-left:${it.indent * UNIT * 0.5}px;color:${colorOf(doc, it.color)}` },
          it.plain ? el("span", {}, stripTex(it.tex)) : math(it.tex, { onlyMath: !it.ko && !String(it.tex).includes("$") }));
        if (it.hl) node.classList.add("st-hl");
        col.append(tag(node, { ...it.meta, id: it.id ?? it.meta.id }, "판서"));
        continue;
      }
      if (it.kind === "derive") {
        const fs = base * (it.scale || 1);
        const box = el("div", { class: "st-derive", style: `margin-left:${it.indent * UNIT * 0.5}px;color:${colorOf(doc, it.color)}` });
        // 모든 단계가 한 동작(derive)에서 나왔으면 묶음 전체를 하나로, step 동작으로 덧붙인 줄은 따로 표시
        const oneAction = it.steps.every((st) => st.meta.seg === it.meta.seg && st.meta.act === it.meta.act);
        it.steps.forEach((st, k) => {
          const parts = st.parts || (st.tex ? [st.tex] : []);
          const row = el("div", { class: "st-step" + (st.box ? " box" : ""), style: `font-size:${fs}px` });
          const eq = el("span", { class: "st-eq" });
          eq.append(math(parts.join(" \\; "), { onlyMath: true }));
          row.append(eq);
          if (st.why) row.append(el("span", { class: "st-why" }, "(∵ ", math(st.why), ")"));
          box.append(oneAction ? row : tag(row, { ...st.meta, id: k === 0 ? it.id : undefined, do: st.meta.do }, k === 0 ? "식 전개" : "전개 단계"));
        });
        col.append(oneAction ? tag(box, { ...it.meta, id: it.id }, "식 전개") : box);
        continue;
      }
      if (it.kind === "problem") {
        col.append(tag(renderProblem(it, doc), it.meta, "문제"));
        continue;
      }
      if (it.kind === "title") {
        col.append(tag(el("div", { class: "st-titlecard" }, it.tag ? el("span", { class: "st-tag" }, it.tag) : null, el("div", { class: "st-big" }, it.title), it.subtitle ? el("div", { class: "st-sub" }, it.subtitle) : null), it.meta, "제목 카드"));
        continue;
      }
      if (it.kind === "end") {
        const node = el("div", { class: "st-end" }, el("div", { class: "st-big" }, it.title));
        it.lines.forEach((ln) => node.append(el("div", { class: "st-line ko", style: `font-size:${base}px` }, math(ln))));
        col.append(tag(node, it.meta, "마무리 카드"));
        continue;
      }
      if (it.kind === "custom") { col.append(tag(el("div", { class: "st-custom" }, "⚙ ", it.fn, " (내가 만든 함수 — 렌더에서만 보임)"), it.meta, "내가 만든 함수")); }
    }
    stage.append(col);
    // 판서 넘침 경고
    requestAnimationFrame(() => { if (col.scrollHeight > col.clientHeight + 4) stage.append(el("div", { class: "st-overflow" }, `⚠ 판서가 칸 아래로 ${Math.round((col.scrollHeight - col.clientHeight) / UNIT * 10) / 10} 만큼 넘칩니다 — 칸을 나누거나 글자 크기를 줄이세요`)); });

    // 자막 띠
    if (opts.subtitle) stage.append(el("div", { class: "st-subtitle" }, opts.subtitle));
    // 칸 표시
    stage.append(el("div", { class: "st-secid" }, `칸 ${S.id}${S.layout === "split" ? " · 그림+판서" : ""}` + (M.order.length > 1 ? `  (${M.order.indexOf(S.id) + 1}/${M.order.length})` : "")));
    for (const w of M.warn) if (w.meta.seg === cursor.seg) stage.append(el("div", { class: "st-overflow", style: "top:8px" }, "⚠ " + w.msg));

    // 스케일
    container.innerHTML = "";
    const wrap = el("div", { class: "stage-wrap" }, stage);
    container.append(wrap);
    const fit = () => { const w = container.clientWidth || W; const s = w / W; stage.style.transform = `scale(${s})`; wrap.style.height = `${H * s}px`; };
    fit();
    if (container.isConnected && !container._stageRO && typeof ResizeObserver !== "undefined") { container._stageRO = new ResizeObserver(() => { const st = container.querySelector(".stage"); const wr = container.querySelector(".stage-wrap"); if (st && wr) { const s = (container.clientWidth || W) / W; st.style.transform = `scale(${s})`; wr.style.height = `${H * s}px`; } }); container._stageRO.observe(container); }
    return { section: S.id, model: M };
  }

  /** 문제: 실제 캡처 그림(image) 또는 수능 지면 양식(paper: 번호·[배점]·(가)(나) 조건 상자·①~⑤), 이전 방식(chalk). */
  const splitTitle = (title) => {
    let t = String(title || "").trim(), num = "", pts = "";
    let m = /^\s*(\d+)\s*\.?\s*/.exec(t); if (m) { num = m[1] + "."; t = t.slice(m[0].length); }
    m = /\[\s*\d+\s*점\s*\]/.exec(t); if (m) { pts = m[0].replace(/\s/g, ""); t = (t.slice(0, m.index) + t.slice(m.index + m[0].length)).trim(); }
    return { num, pts, rest: t };
  };
  const isCond = (s) => /^\s*\((가|나|다|라|ㄱ|ㄴ|ㄷ)\)/.test(String(s));
  function renderProblem(it, doc) {
    const node = el("div", { class: "st-problem st-paper" + (it.docked ? " docked" : "") + (it.style === "chalk" ? " chalkstyle" : "") });
    if (it.style === "image" && it.image) {
      const pid = (doc.meta || {}).id || "";
      node.append(el("img", { class: "st-pimg", src: `/projects/${pid}/${it.image}`, alt: it.image,
        onerror: (e) => { e.target.replaceWith(el("div", { class: "st-pmissing" }, `그림 파일을 찾을 수 없습니다: projects/${pid}/${it.image}`)); } }));
      return node;
    }
    if (it.style === "chalk") {
      node.classList.remove("st-paper");
      if (it.title) node.append(el("div", { class: "st-ptitle" }, it.title));
      it.lines.forEach((ln, k) => node.append(el("div", { class: "st-pline" + (it.focus === k ? " focus" : "") + (it.focus !== null && it.focus !== k ? " dimmed" : "") }, math(ln))));
    } else {
      const { num, pts, rest } = splitTitle(it.title);
      const lines = rest ? [rest, ...it.lines] : [...it.lines];
      const body = el("div", { class: "st-pbody" });
      let k = 0;
      const showPts = pts && !lines.join(" ").includes(pts);
      const lineNode = (idx) => el("div", { class: "st-pline" + (it.focus === idx ? " focus" : "") + (it.focus !== null && it.focus !== idx ? " dimmed" : "") },
        math(lines[idx]), showPts && idx === lines.length - 1 ? el("b", { class: "st-pts" }, " " + pts) : null);
      while (k < lines.length) {
        if (isCond(lines[k])) {
          const box = el("div", { class: "st-pcond" });
          while (k < lines.length && isCond(lines[k])) box.append(lineNode(k++));
          body.append(box);
        } else {
          body.append(lineNode(k++));
        }
      }
      if (it.choices && !it.docked) {
        const ch = el("div", { class: "st-choices" });
        // 보기는 $ 없이 수식만 쓰는 형식 (예: 2^{-1}, \frac12)
        it.choices.forEach((c, i) => ch.append(el("span", { class: "st-choice" + (it.answer && it.answer.choice === i + 1 ? " ans" : "") }, "①②③④⑤⑥⑦⑧⑨"[i] || `${i + 1}.`, " ", math(c, { onlyMath: !String(c).includes("$") }))));
        body.append(ch);
      }
      node.append(num ? el("div", { class: "st-pnum" }, num) : null, body);
    }
    return node;
  }

  /** 커서 동작까지만 적용했을 때의 카메라 칸 (goto 가 커서면 목적지). */
  function simulateUntil(doc, cursor) {
    const clone = { ...doc, segments: (doc.segments || []).slice(0, cursor.seg + 1).map((s, i) => i === cursor.seg ? { ...s, actions: (s.actions || []).slice(0, cursor.act + 1) } : s) };
    return simulate(clone, cursor.seg);
  }

  function renderGraph(g, box, M, doc, tag, cursor) {
    const svg = el("svg:svg", { class: "st-graph", viewBox: `0 0 ${box.w} ${box.h}`, style: `left:${box.x}px;top:${box.y}px;width:${box.w}px;height:${box.h}px` });
    if (!g) { svg.append(el("svg:text", { x: box.w / 2, y: box.h / 2, class: "st-gempty", "text-anchor": "middle" }, "그림 영역 — ‘좌표축’ 동작을 넣으면 여기에 그래프가 그려집니다")); return svg; }
    const pad = 28; let [x0, x1] = g.xr, [y0, y1] = g.yr;
    if (!isFinite(x0) || !isFinite(x1) || x1 <= x0) [x0, x1] = [-4, 4];
    if (!isFinite(y0) || !isFinite(y1) || y1 <= y0) [y0, y1] = [-3, 3];
    let sx = (box.w - 2 * pad) / (x1 - x0), sy = (box.h - 2 * pad) / (y1 - y0);
    if (g.equal) { const s = Math.min(sx, sy); sx = sy = s; }
    const cx = pad + (box.w - 2 * pad - sx * (x1 - x0)) / 2, cy = pad + (box.h - 2 * pad - sy * (y1 - y0)) / 2;
    const X = (x) => cx + (x - x0) * sx, Y = (y) => cy + (y1 - y) * sy;
    const axisC = colorOf(doc, "axis_sym");
    const ax = el("svg:g", { class: "st-axes" });
    ax.append(el("svg:line", { x1: X(x0), y1: Y(0), x2: X(x1), y2: Y(0), stroke: axisC, "stroke-width": 2, "marker-end": "url(#st-arr)" }));
    ax.append(el("svg:line", { x1: X(0), y1: Y(y0), x2: X(0), y2: Y(y1), stroke: axisC, "stroke-width": 2, "marker-end": "url(#st-arr)" }));
    svg.append(el("svg:defs", {}, el("svg:marker", { id: "st-arr", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, el("svg:path", { d: "M0,0 L10,5 L0,10 z", fill: axisC }))));
    if (g.numbers) {
      const stepX = g.xr[2] || niceStep(x1 - x0), stepY = g.yr[2] || niceStep(y1 - y0);
      for (let x = Math.ceil(x0 / stepX) * stepX; x <= x1 + 1e-9; x += stepX) if (Math.abs(x) > 1e-9) ax.append(el("svg:text", { x: X(x), y: Y(0) + 16, class: "st-num", "text-anchor": "middle" }, fmtNum(x)));
      for (let y = Math.ceil(y0 / stepY) * stepY; y <= y1 + 1e-9; y += stepY) if (Math.abs(y) > 1e-9) ax.append(el("svg:text", { x: X(0) - 8, y: Y(y) + 4, class: "st-num", "text-anchor": "end" }, fmtNum(y)));
    }
    if (g.labels !== false) { ax.append(el("svg:text", { x: X(x1) - 4, y: Y(0) - 8, class: "st-axl" }, "x")); ax.append(el("svg:text", { x: X(0) + 8, y: Y(y1) + 14, class: "st-axl" }, "y")); }
    svg.append(g.meta ? tag(ax, g.meta, "좌표축") : ax);

    const curve = (f, xr, color, dashed, sw) => {
      const [a, b] = xr || [x0, x1]; const n = 240; let d = "", pen = false;
      for (let i = 0; i <= n; i++) {
        const x = a + (b - a) * i / n; let y; try { y = f(x); } catch (_) { y = NaN; }
        if (typeof y === "boolean") y = NaN;
        if (!isFinite(y) || y < y0 - 0.2 * (y1 - y0) || y > y1 + 0.2 * (y1 - y0)) { pen = false; continue; }
        const yy = Math.max(y0 - 0.05 * (y1 - y0), Math.min(y1 + 0.05 * (y1 - y0), y));
        d += `${pen ? "L" : "M"}${X(x).toFixed(1)},${Y(yy).toFixed(1)} `; pen = true;
      }
      const path = el("svg:path", { d, fill: "none", stroke: color, "stroke-width": sw || 3.5, "stroke-dasharray": dashed ? "7 6" : null, "stroke-linecap": "round" });
      // 얇은 곡선도 클릭할 수 있게 투명한 넓은 선을 함께 둔다
      return el("svg:g", {}, el("svg:path", { d, fill: "none", stroke: "transparent", "stroke-width": 18, "pointer-events": "stroke" }), path);
    };
    const labelAt = (e, color, px, py) => {
      const [dx, dy] = DIR[e.label_dir] || DIR.UR;
      return el("svg:foreignObject", { x: px + dx * 14 - (dx < 0 ? 140 : 0), y: py + dy * 14 - (dy < 0 ? 30 : 0), width: 140, height: 34 },
        Object.assign(el("div", { class: "st-glabel", style: `color:${color};text-align:${dx < 0 ? "right" : "left"}` }, math(e.label, { onlyMath: !String(e.label).includes("$") })), { xmlns: "http://www.w3.org/1999/xhtml" }));
    };
    for (const e of g.elems) {
      const color = colorOf(doc, e.color, "#f2f2e6");
      const grp = el("svg:g", {});
      if ((e.kind === "plot" || e.kind === "line") && e.f) {
        grp.append(curve(e.f, e.xr, color, e.dashed, e.stroke));
        if (e.label) { const lx = e.label_at !== undefined && e.label_at !== null ? M.env.num(e.label_at) : (e.xr ? e.xr[1] : x1) * 0.8; let ly; try { ly = e.f(lx); } catch (_) { ly = NaN; } if (isFinite(ly)) grp.append(labelAt(e, color, X(lx), Y(Math.max(y0, Math.min(y1, ly))))); }
      } else if (e.kind === "plot" || e.kind === "line") {
        grp.append(el("svg:text", { x: 10, y: 20 + g.elems.indexOf(e) * 18, class: "st-gwarn" }, `∿ ${e.id || ""}: ${e.expr || "(식 해석 불가)"} — 식을 읽지 못해 렌더에서만 보임`));
      } else if (e.kind === "vline") {
        grp.append(el("svg:line", { x1: X(e.x), y1: Y(y0), x2: X(e.x), y2: Y(y1), stroke: "transparent", "stroke-width": 18, "pointer-events": "stroke" }));
        grp.append(el("svg:line", { x1: X(e.x), y1: Y(y0), x2: X(e.x), y2: Y(y1), stroke: color, "stroke-width": e.stroke || 2.4, "stroke-dasharray": e.dashed === false ? null : "6 6" }));
        if (e.label) grp.append(labelAt(e, color, X(e.x), Y(y1) + 10));
      } else if (e.kind === "point") {
        grp.append(el("svg:circle", { cx: X(e.p[0]), cy: Y(e.p[1]), r: 16, fill: "transparent" }));
        if (e.from) grp.append(el("svg:line", { x1: X(e.from[0]), y1: Y(e.from[1]), x2: X(e.p[0]), y2: Y(e.p[1]), stroke: color, "stroke-width": 1.5, "stroke-dasharray": "4 4", "marker-end": e.arrow ? "url(#st-arr)" : null }));
        grp.append(el("svg:circle", { cx: X(e.p[0]), cy: Y(e.p[1]), r: 6, fill: colorOf(doc, e.color, colorOf(doc, "point")) }));
        if (e.label) grp.append(labelAt(e, colorOf(doc, e.color, "#f2f2e6"), X(e.p[0]), Y(e.p[1])));
      } else if ((e.kind === "segment" || e.kind === "arrow") && e.a && e.b) {
        grp.append(el("svg:line", { x1: X(e.a[0]), y1: Y(e.a[1]), x2: X(e.b[0]), y2: Y(e.b[1]), stroke: color, "stroke-width": e.stroke || 3, "stroke-dasharray": e.dashed ? "6 6" : null, "marker-end": e.kind === "arrow" ? "url(#st-arr)" : null }));
        if (e.label) grp.append(labelAt(e, color, (X(e.a[0]) + X(e.b[0])) / 2, (Y(e.a[1]) + Y(e.b[1])) / 2));
      } else if (e.kind === "polygon" && e.pts.length) {
        grp.append(el("svg:polygon", { points: e.pts.map((p) => `${X(p[0])},${Y(p[1])}`).join(" "), fill: color, "fill-opacity": e.fill ?? 0.08, stroke: color, "stroke-width": e.stroke || 3, "stroke-dasharray": e.dashed ? "6 6" : null }));
      } else if (e.kind === "guides" && e.p) {
        grp.append(el("svg:line", { x1: X(e.p[0]), y1: Y(e.p[1]), x2: X(e.p[0]), y2: Y(0), stroke: color, "stroke-width": 1.5, "stroke-dasharray": "4 4" }));
        grp.append(el("svg:line", { x1: X(e.p[0]), y1: Y(e.p[1]), x2: X(0), y2: Y(e.p[1]), stroke: color, "stroke-width": 1.5, "stroke-dasharray": "4 4" }));
        if (e.xl) grp.append(labelAt({ label: e.xl, label_dir: "DOWN" }, color, X(e.p[0]), Y(0) + 6));
        if (e.yl) grp.append(labelAt({ label: e.yl, label_dir: "LEFT" }, color, X(0) - 6, Y(e.p[1])));
      } else if (e.kind === "label" && e.text) {
        const p = e.p || [x0 + (x1 - x0) * 0.1, y1 - (y1 - y0) * 0.1];
        grp.append(labelAt({ label: e.text, label_dir: e.dir || "UR" }, color, X(p[0]), Y(p[1])));
      } else if (e.kind === "custom") {
        if (e.f) grp.append(curve(e.f, null, color, true, 3));
        const k = g.elems.filter((x) => x.kind === "custom").indexOf(e);
        grp.append(el("svg:foreignObject", { x: 8, y: box.h - 34 - k * 28, width: box.w - 16, height: 26 },
          Object.assign(el("div", { class: "st-customchip" }, `⚙ ${e.fn}${e.f ? "" : " — 내가 만든 함수 (렌더에서만 정확히 보임)"}`), { xmlns: "http://www.w3.org/1999/xhtml" })));
      } else continue;
      svg.append(tag(grp, { ...e.meta, id: e.id ?? e.meta.id }, ({ plot: "함수 그래프", line: "직선", vline: "세로선", point: "점", segment: "선분", arrow: "화살표", polygon: "다각형", guides: "보조선", label: "라벨", custom: "내가 만든 함수" })[e.kind]));
    }
    return svg;
  }
  const niceStep = (range) => { const raw = range / 8; const p = Math.pow(10, Math.floor(Math.log10(raw))); const n = raw / p; return (n < 1.5 ? 1 : n < 3.5 ? 2 : n < 7.5 ? 5 : 10) * p; };
  const fmtNum = (v) => (Math.abs(v - Math.round(v)) < 1e-9 ? String(Math.round(v)) : v.toFixed(1));

  // ------------------------------------------------------------------ 썸네일 (장면 목록)
  const thumbCache = new Map();
  function thumbnail(doc, segIdx, width = 200) {
    const key = JSON.stringify([doc.meta?.style, doc.layout, doc.params, (doc.segments || []).slice(0, segIdx + 1).map((s) => s.actions)]);
    const holder = document.createElement("div");
    holder.className = "stage-thumb"; holder.style.width = width + "px"; holder.style.height = Math.round(width * H / W) + "px";
    let html = thumbCache.get(key);
    if (!html) {
      const tmp = document.createElement("div"); tmp.style.width = W + "px";
      try { render(tmp, doc, { cursor: { seg: segIdx, act: null } }); } catch (_) { return null; }
      const st = tmp.querySelector(".stage"); if (!st) return null;
      st.style.transform = ""; html = st.outerHTML;
      thumbCache.set(key, html); if (thumbCache.size > 60) thumbCache.delete(thumbCache.keys().next().value);
    }
    holder.innerHTML = html;
    const st = holder.firstElementChild; st.style.transform = `scale(${width / W})`; st.classList.add("thumb");
    return holder;
  }

  return { simulate, render, thumbnail, pyToJs, makeEnv, W, H };
})();
