/* Explainer Studio – 프론트엔드 (외부 의존성: 수식 미리보기용 KaTeX 만 선택적으로 사용) */
(() => {
  "use strict";

  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
  const el = (tag, attrs = {}, ...children) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") n.className = v;
      else if (k === "html") n.innerHTML = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) n.append(c.nodeType ? c : document.createTextNode(String(c)));
    return n;
  };
  const LS = { get: (k, d) => { try { const v = localStorage.getItem("studio." + k); return v === null ? d : JSON.parse(v); } catch (_) { return d; } }, set: (k, v) => { try { localStorage.setItem("studio." + k, JSON.stringify(v)); } catch (_) {} } };

  const state = {
    projects: [], pid: null, doc: null, yamlText: "", yamlDirty: false, dirty: false,
    catalog: [], catalogByName: {}, hooks: [], sel: 0, outputs: null, job: null, logOffset: 0,
    timing: null, pollTimer: null, rawOpen: new Set(),
    expanded: new Set(),      // 펼쳐진 동작 카드
    sentences: {},            // 장면 id → {exact, sentences:[{i,text,start?}], narr}  (서버: TTS 캐시 기준 실제 문장 경계)
    pro: LS.get("pro", false),
    past: [], future: [], snap: null, lastTouch: { key: null, t: 0 },   // 되돌리기
    stage: 0, lastCheck: null,
    cursor: { seg: -1, act: null },   // 무대에서 강조할 동작 (편집 중인 카드)
    stageMode: "stage",               // stage(즉시 미리보기) | render(렌더 화면)
  };
  window.__studio = state;    // 브라우저 콘솔에서 상태를 들여다볼 수 있게 (디버깅용)

  // ------------------------------------------------------------------ API
  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...opts, body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
    if (!res.ok) {
      let msg = res.statusText;
      try { msg = (await res.json()).detail || msg; } catch (_) {}
      throw new Error(msg);
    }
    return res.json();
  }

  function toast(msg, kind = "") {
    const t = $("#toast");
    t.textContent = msg; t.className = kind; t.classList.remove("hidden");
    clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), 3600);
  }

  function setDirty(v) {
    state.dirty = v;
    const dot = $("#dirtyDot"), btn = $("#btnSave");
    dot.classList.toggle("on", v);
    btn.classList.toggle("dirty-on", v);
    btn.textContent = "";
    btn.append(dot, v ? "저장 *" : "저장");
    updateNextHint();
  }

  // ------------------------------------------------------------------ 값 표시/파싱
  const fmtVal = (v) => (typeof v === "string" ? v : JSON.stringify(v));
  function parseVal(s) {
    const t = String(s ?? "").trim();
    if (t === "") return undefined;
    if (/^(true|false|null)$/.test(t)) return JSON.parse(t);
    if (/^-?\d+(\.\d+)?$/.test(t)) return Number(t);
    if (/^[\[{"]/.test(t)) { try { return JSON.parse(t); } catch (_) { return s; } }
    return s;
  }
  /** "1, 2" / "-3, 3, 1" 같은 숫자 목록 → 배열. 숫자가 아니면 문자열 그대로 (예: 점 이름). */
  function parseList(s) {
    const t = String(s ?? "").trim();
    if (t === "") return undefined;
    if (/^[\[{]/.test(t)) { try { return JSON.parse(t); } catch (_) { return t; } }
    const items = t.split(/\s*,\s*/).filter((x) => x.length);
    return items.map((x) => (/^-?\d+(\.\d+)?$/.test(x) ? Number(x) : x));
  }
  const splitSentences = (text) => (text || "").trim().split(/(?<=[.?!…])\s+/).filter(Boolean);
  const normNarr = (t) => (t || "").split(/\s+/).filter(Boolean).join(" ");
  function sentencesFor(seg) {
    const info = state.sentences[seg.id];
    if (info && info.exact && info.narr === normNarr(seg.narration)) return { exact: true, list: info.sentences };
    return { exact: false, list: splitSentences(seg.narration).map((t, i) => ({ i: i + 1, text: t })) };
  }
  function setSentences(map, doc) {
    const byId = {};
    for (const sg of (doc || state.doc || {}).segments || []) byId[sg.id] = sg;
    for (const [id, info] of Object.entries(map || {})) {
      state.sentences[id] = { exact: !!info.exact, sentences: info.sentences || [], narr: normNarr((byId[id] || {}).narration) };
    }
  }
  const PART_SEP = " | ";
  const joinParts = (parts) => (parts || []).join(PART_SEP);
  const splitParts = (s) => s.split(/\s*\|\s*/).map((x) => x.trim()).filter((x) => x.length);

  // ------------------------------------------------------------------ 수식 미리보기 (KaTeX 가 있으면 실제 조판, 없으면 읽기 쉬운 텍스트)
  const hasKatex = () => typeof window.katex !== "undefined";
  function katexInto(node, tex, display = false) {
    try { window.katex.render(tex, node, { throwOnError: false, displayMode: display, strict: "ignore", trust: true }); return true; }
    catch (e) { node.textContent = stripTex(tex); return false; }
  }
  /** "$x^2$ 의 값은?" 처럼 글과 수식이 섞인 문자열을 한 줄로 조판. onlyMath=true 면 전체를 수식으로. */
  function mathLine(str, { onlyMath = false, ko = false } = {}) {
    const span = el("span", { class: ko ? "ko" : "" });
    const s = String(str ?? "");
    if (!hasKatex()) { span.textContent = stripTex(s); span.classList.add("plain"); return span; }
    if (onlyMath && !s.includes("$")) { katexInto(span, s); return span; }
    const parts = s.split(/(\$[^$]*\$)/g);
    for (const p of parts) {
      if (!p) continue;
      if (p.startsWith("$") && p.endsWith("$") && p.length > 1) { const m = el("span"); katexInto(m, p.slice(1, -1)); span.append(m); }
      else span.append(el("span", { class: "txt" }, p));
    }
    return span;
  }
  function mathPreview(values, { onlyMath = false, ko = false } = {}) {
    const list = Array.isArray(values) ? values : [values];
    const box = el("div", { class: "mathprev" + (list.length > 1 ? " multi" : "") });
    if (!hasKatex()) box.append(el("span", { class: "badge", title: "KaTeX 를 불러오지 못해(오프라인?) 텍스트로 대신 보여줍니다" }, "텍스트"));
    for (const v of list) box.append(mathLine(v, { onlyMath, ko }));
    return box;
  }
  /** 자주 쓰는 수식 기호 툴바 — 클릭하면 입력란 커서 위치에 끼워 넣는다. */
  const SYMBOLS = [
    ["분수", "\\dfrac{a}{b}"], ["제곱", "^{2}"], ["아래첨자", "_{n}"], ["루트", "\\sqrt{x}"], ["Σ", "\\sum_{k=1}^{n}"], ["∫", "\\int_{a}^{b}"],
    ["lim", "\\lim_{x\\to 0}"], ["×", "\\times"], ["·", "\\cdot"], ["≤", "\\le"], ["≥", "\\ge"], ["≠", "\\ne"], ["→", "\\to"], ["⇒", "\\Rightarrow"],
    ["∞", "\\infty"], ["π", "\\pi"], ["θ", "\\theta"], ["log", "\\log_{2}"], ["ln", "\\ln"], ["( )", "\\left( \\right)"], ["∴", "\\therefore"], ["빈칸", "\\quad"],
  ];
  function symbolBar(target, onInsert) {
    const bar = el("div", { class: "symbar" }, el("span", { class: "lab" }, "기호"));
    for (const [label, code] of SYMBOLS) {
      bar.append(el("button", { type: "button", title: code, onclick: () => {
        const s = target.selectionStart ?? target.value.length, e = target.selectionEnd ?? s;
        target.value = target.value.slice(0, s) + code + target.value.slice(e);
        target.focus(); target.selectionStart = target.selectionEnd = s + code.length;
        onInsert && onInsert();
      } }, label));
    }
    return bar;
  }

  // ------------------------------------------------------------------ 프로젝트 로드
  async function loadProjects() {
    state.projects = await api("/api/projects");
    const sel = $("#projectSelect");
    sel.innerHTML = "";
    for (const p of state.projects) {
      sel.append(el("option", { value: p.id }, `${p.title}${p.running ? "  ⏳" : p.has_final ? "  ✓" : ""}`));
    }
    if (state.pid) sel.value = state.pid;
  }

  async function openProject(pid) {
    if (state.dirty && !confirm("저장하지 않은 변경이 있습니다. 버릴까요?")) { $("#projectSelect").value = state.pid; return; }
    const data = await api(`/api/projects/${pid}`);
    state.pid = pid; state.doc = data.doc; state.yamlText = data.yaml; state.yamlDirty = false;
    state.hooks = data.hooks || []; state.outputs = data.outputs; state.sel = 0; state.timing = null;
    state.rawOpen.clear(); state.sentences = {}; setSentences(data.sentences, data.doc);
    state.past = []; state.future = []; state.lastCheck = null; showCheckBadge(null);
    setDirty(false);
    if (data.parse_error) toast("YAML 파싱 오류: " + data.parse_error + " — 고급 모드의 YAML 원문에서 고치세요", "bad");
    if (!state.doc) { state.doc = { meta: { id: pid, title: pid }, segments: [] }; }
    if (!Array.isArray(state.doc.segments)) state.doc.segments = [];
    state.snap = JSON.stringify(state.doc);
    if ((data.autofix || []).length) { setDirty(true); toast(`${data.autofix.join(" · ")} — 저장하면 파일에 반영됩니다`, "ok"); }
    location.hash = pid;
    $("#projectSelect").value = pid;
    renderAll();
    if (data.job) attachJob(data.job);
    else updateJobStatus(null);
  }

  function renderAll() {
    renderSegList();
    renderSegEditor();
    renderSettings();
    renderOutputs();
    renderTimeline();
    $("#yamlText").value = state.yamlText;
    updateUndoButtons();
  }

  // ------------------------------------------------------------------ 되돌리기 / 다시하기
  /** 문서를 바꾼 뒤 부르는 함수. coalesce 키가 같고 1초 안이면 하나의 되돌리기 단위로 합친다 (타이핑). */
  function touched(coalesce = null) {
    const now = Date.now();
    const cur = JSON.stringify(state.doc);
    if (state.snap !== null && cur !== state.snap) {
      const merge = coalesce && state.lastTouch.key === coalesce && now - state.lastTouch.t < 1200 && state.past.length;
      if (!merge) { state.past.push(state.snap); if (state.past.length > 100) state.past.shift(); }
      state.future = [];
    }
    state.snap = cur; state.lastTouch = { key: coalesce, t: now };
    setDirty(true); state.yamlDirty = false;
    updateUndoButtons();
    // 장면 목록의 슬라이드 썸네일을 편집에 맞춰 갱신 (타이핑 중에는 잠깐 모아서)
    clearTimeout(state._listTimer); state._listTimer = setTimeout(renderSegList, 250);
  }
  function restoreDoc(json) {
    const seg = state.doc.segments[state.sel];
    const openIdx = seg ? (seg.actions || []).map((a, i) => (state.expanded.has(a) ? i : -1)).filter((i) => i >= 0) : [];
    state.doc = JSON.parse(json); state.snap = json;
    state.sel = Math.min(state.sel, Math.max(0, state.doc.segments.length - 1));
    state.expanded.clear();
    const s2 = state.doc.segments[state.sel];
    if (s2) for (const i of openIdx) if (s2.actions?.[i]) state.expanded.add(s2.actions[i]);
    setDirty(true); state.yamlDirty = false;
    renderSegList(); renderSegEditor(); if (!$("#settingsEditor").classList.contains("hidden")) renderSettings();
    updateUndoButtons();
  }
  function undo() { if (!state.past.length) return; state.future.push(JSON.stringify(state.doc)); restoreDoc(state.past.pop()); toast("되돌렸습니다 (Ctrl+Y 로 다시)"); }
  function redo() { if (!state.future.length) return; state.past.push(JSON.stringify(state.doc)); restoreDoc(state.future.pop()); }
  function updateUndoButtons() { $("#btnUndo").disabled = !state.past.length; $("#btnRedo").disabled = !state.future.length; }

  // ------------------------------------------------------------------ 동작 표시 정보 (아이콘·한글 이름·분류 색)
  const CAT_COLOR = {
    "카드·전환": "#b48cff", "문제": "#7cc4ff", "칠판 판서": "#ffd23f", "식 전개": "#ff9f43",
    "그래프": "#5ad48a", "보드(panel 스타일)": "#4fd1c5", "사용자 정의": "#ff7ab6",
  };
  const ACTION_META = {
    title_card: ["제목 카드", "▣"], end_card: ["마무리 카드", "▤"], section: ["섹션 배너", "▭"], wait: ["잠깐 멈춤", "⏸"],
    clear: ["화면 지우기", "⌫"], fade: ["사라지기", "◌"], dim: ["흐리게", "◐"], undim: ["다시 선명하게", "◑"], highlight: ["강조", "✦"],
    problem: ["문제 전문", "≣"], problem_focus: ["읽는 줄 강조", "▶"], problem_dock: ["문제 축소", "⬒"], answer: ["정답 표시", "✔"],
    caption: ["설명 말풍선", "❝"], goto: ["칠판 칸 이동", "➜"], write: ["판서", "✍"], space: ["줄 띄우기", "␣"], camera: ["카메라 줌", "◎"],
    derive: ["식 전개", "∑"], step: ["전개 한 단계", "↳"], axes: ["좌표축", "┼"], plot: ["함수 그래프", "∿"], line: ["직선", "╱"],
    vline: ["세로선", "│"], point: ["점", "•"], points: ["점 여러 개", "∴"], polygon: ["다각형", "⬠"], segment: ["선분", "—"],
    arrow: ["화살표", "→"], guides: ["좌표 보조선", "⌐"], translate_copy: ["평행이동 복사", "⇢"], reflect: ["대칭이동", "⇋"],
    label: ["라벨", "🏷"], board_init: ["보드 만들기", "▦"], board: ["보드 만들기", "▦"], board_write: ["보드 쓰기", "▦"], board_replace: ["보드 바꾸기", "▦"],
    board_highlight: ["보드 강조", "▦"], board_clear: ["보드 지우기", "▦"], board_title: ["보드 제목", "▦"], custom: ["내가 만든 함수", "⚙"],
  };
  const FAVORITES = ["write", "derive", "caption", "goto", "highlight", "problem", "answer", "plot", "point", "custom", "wait"];
  /** 팔레트·카드에 보이는 쉬운 설명 (없으면 파이썬 docstring 첫 줄). */
  const DOC_KO = {
    write: "칠판에 손글씨로 한 줄씩 적습니다. 한글과 수식을 섞어 쓸 수 있어요.", derive: "식을 한 줄씩 변형해 가는 애니메이션. 앞 줄과 같은 조각은 미끄러지고, 바뀐 조각만 강조됩니다.",
    step: "이미 시작한 식 전개에 한 단계를 더합니다 (다른 문장에 맞춰 이어 쓸 때).", caption: "그래프 아래에 한 줄 설명 말풍선을 띄웁니다. 새 말풍선을 띄우면 이전 것은 바뀝니다.",
    goto: "카메라를 다음 칠판 칸으로 옮깁니다. 처음 가는 칸이면 제목을 판서합니다.", highlight: "그래프·식·점을 짚어 주거나 반짝이게 해서 시선을 모읍니다.",
    problem: "문제 전문을 화면 중앙에 크게 보여줍니다 (제목·줄·보기).", problem_focus: "문제의 특정 줄만 밝게 해서 지금 읽는 곳을 표시합니다.", problem_dock: "중앙의 문제를 위쪽 작은 헤더로 줄여 자리를 비웁니다.",
    answer: "정답을 표시합니다 — 보기 번호에 동그라미, 또는 수식을 상자로.", plot: "y = f(x) 그래프를 그립니다. 식은 파이썬 문법(x**2, exp(x)).", point: "점 하나를 찍습니다. 라벨과 색을 붙일 수 있어요.",
    points: "여러 점을 차례로 찍습니다.", line: "직선을 그립니다 (기울기·y절편, 또는 두 점).", vline: "x = a 세로 점선 (점근선 등).", axes: "좌표축을 그립니다. x·y 범위를 정할 수 있어요.",
    custom: "프로젝트 폴더 hooks.py 에 만든 파이썬 함수를 실행합니다 (복잡한 애니메이션용).", wait: "지정한 초만큼 아무것도 하지 않고 기다립니다.",
    clear: "화면의 대상(또는 전체)을 지웁니다.", fade: "대상을 서서히 사라지게(또는 나타나게) 합니다.", dim: "대상을 흐리게 해서 뒤로 물립니다.", undim: "흐려진 대상을 다시 선명하게.",
    title_card: "영상 맨 앞의 제목 카드.", end_card: "마무리 카드 — 정리 문장을 써 내려갑니다.", section: "화면 위쪽에 작은 소제목 배너.", camera: "카메라를 특정 대상·좌표로 줌인/줌아웃.",
    space: "판서 커서를 아래로 내려 문단 사이 여백을 둡니다.", label: "수식 라벨을 대상 옆이나 좌표에 붙입니다.", guides: "점에서 축으로 내린 점선과 좌표값.", segment: "두 점을 잇는 선분.", arrow: "두 점 사이 화살표.",
    polygon: "점들을 이어 다각형(영역)을 그립니다.", reflect: "점을 직선에 대해 대칭이동한 점을 만듭니다.", translate_copy: "점이나 그래프를 평행이동한 복사본을 만듭니다.",
  };
  const actDoc = (name) => DOC_KO[name] || state.catalogByName[name]?.doc || "";
  const actLabel = (name) => (ACTION_META[name] || [name])[0];
  const actIcon = (name) => (ACTION_META[name] || [null, "▪"])[1];
  const actColor = (name) => CAT_COLOR[state.catalogByName[name]?.category] || "#8b93a7";
  const short = (s, n = 60) => { s = String(s ?? ""); return s.length > n ? s.slice(0, n - 1) + "…" : s; };
  const stripTex = (s) => String(s ?? "").replace(/\\(tfrac|dfrac|frac)\{([^}]*)\}\{([^}]*)\}/g, "$2/$3").replace(/\\(tfrac|dfrac|frac)(\d)(\d)/g, "$2/$3")
    .replace(/\\(Bigl|Bigr|bigl|bigr|Big|big|left|right)\b/g, "").replace(/\\mathrm\{([^}]*)\}/g, "$1").replace(/\\(cdots|ldots|dots)\b/g, "…").replace(/\\ /g, " ")
    .replace(/\\(quad|qquad|;|,|!)/g, " ").replace(/\\(Rightarrow|to|xrightarrow)/g, "→").replace(/\\(times|cdot)/g, "×").replace(/\\(log|therefore|checkmark)/g, (m) => ({ "\\log": "log", "\\therefore": "∴", "\\checkmark": "✓" })[m])
    .replace(/\\[a-zA-Z]+/g, (m) => m.slice(1)).replace(/[{}$]/g, "").replace(/\s+/g, " ").trim();

  /** 카드 머리에 보일 한 줄 요약(텍스트). */
  function summarize(act) {
    const a = act, j = (v) => (Array.isArray(v) ? v.join(", ") : v === undefined ? "" : String(v));
    switch (a.do) {
      case "goto": return `→ ${sectionName(a.section)}`;
      case "title_card": case "end_card": return short(a.title ?? "");
      case "write": return short(stripTex(a.text ?? a.tex ?? (a.lines || []).join("  /  ")));
      case "caption": return short(stripTex(a.text ?? a.tex ?? ""));
      case "problem": return `${a.title ?? ""} · ${(a.lines || []).length}줄${a.choices ? ` · 보기 ${a.choices.length}개` : ""}`;
      case "problem_focus": return `${(a.index ?? 0) + 1}번째 줄`;
      case "answer": return a.tex ? stripTex(a.tex) : a.choice ? `보기 ${a.choice}번에 동그라미` : "";
      case "derive": { const st = a.steps || []; return `${st.length}단계` + (st[0] ? ` — ${short(stripTex((st[0].parts || [st[0].tex]).join(" ")), 40)}` : ""); }
      case "step": return `${a.of ?? "d"} ← ${short(stripTex((a.parts || [a.tex]).join(" ")), 48)}`;
      case "axes": return [a.x_range ? `x ${j(a.x_range)}` : "", a.y_range ? `y ${j(a.y_range)}` : ""].filter(Boolean).join("  ") || "기본 범위";
      case "plot": return `${a.id ?? ""}:  y = ${a.expr ?? ""}` + (a.label ? `   (${stripTex(a.label)})` : "");
      case "line": return `${a.id ?? ""}: ` + (a.expr ? `y = ${a.expr}` : `y = ${a.slope ?? "?"}·x + ${a.intercept ?? 0}`);
      case "vline": return `${a.id ?? ""}: x = ${a.x}`;
      case "points": return (a.items || []).map((it) => it.id).join(", ");
      case "point": return `${a.id ?? ""} (${j(a.pos)})`;
      case "polygon": return j(a.points);
      case "segment": case "arrow": return `${a.a} → ${a.b}`;
      case "guides": return `${a.point} 의 좌표 보조선`;
      case "reflect": return `${a.source} → ${a.id}  (y = ${a.slope}x + ${a.intercept})`;
      case "translate_copy": return `${a.source} → (${a.dx}, ${a.dy})`;
      case "highlight": return `${j(a.ids)}  · ${MODE_KO[a.mode ?? "indicate"] || a.mode}`;
      case "dim": case "undim": case "fade": return j(a.ids);
      case "camera": return a.reset ? "원래 뷰로" : a.sections ? `칸 ${j(a.sections)} 전체` : a.ids ? `${j(a.ids)} 이 보이게` : a.focus ?? (a.pos ? `(${j(a.pos)})` : "");
      case "custom": { const ps = Object.entries(a).filter(([k]) => !["do", "fn", "at", "run_time"].includes(k)).slice(0, 3).map(([k, v]) => `${k}=${short(fmtVal(v), 18)}`); return `${a.fn}(${ps.join(", ")})`; }
      case "wait": return `${a.seconds ?? 1}초`;
      case "label": return short(stripTex(a.text ?? a.tex ?? ""));
      case "section": return short(a.text ?? "");
      default: { const ps = Object.entries(a).filter(([k, v]) => !["do", "at", "run_time"].includes(k) && (typeof v === "string" || typeof v === "number")).slice(0, 2); return ps.map(([k, v]) => `${paramLabel(a.do, k)}: ${short(String(v), 24)}`).join(" · "); }
    }
  }
  /** 카드 머리 요약을 가능하면 수식 조판으로. */
  function summaryNode(act) {
    const a = act;
    if (hasKatex()) {
      if ((a.do === "write" || a.do === "caption" || a.do === "label" || a.do === "board_write" || a.do === "board_replace") && (a.tex || a.text || a.lines)) {
        const v = a.tex ?? a.text ?? (a.lines || []).join("  /  ");
        return mathLine(v, { onlyMath: a.tex !== undefined && !String(a.tex).includes("$") });
      }
      if (a.do === "answer" && a.tex) return mathLine(a.tex, { onlyMath: !String(a.tex).includes("$") });
      if ((a.do === "derive" && a.steps?.[0]) || a.do === "step") {
        const st = a.do === "derive" ? a.steps[0] : a;
        const tex = (st.parts || [st.tex || ""]).join(" ");
        const w = el("span"); if (a.do === "derive") w.append(`${a.steps.length}단계 — `); else w.append(`${a.of ?? "d"} ← `);
        const m = el("span"); katexInto(m, tex); w.append(m); return w;
      }
    }
    return document.createTextNode(summarize(act));
  }
  const atText = (at) => (at === undefined || at === null || at === "" ? "" : typeof at === "number" ? `${at}s` : String(at));
  const MODE_KO = { indicate: "짚어 주기", flash: "번쩍", circumscribe: "테두리", wiggle: "흔들기", pulse: "펄스" };
  function sectionName(id) {
    const s = (state.doc?.layout?.chalk?.sections || []).find((x) => x.id === id);
    return s ? `${s.title || s.id}${s.title ? ` (${s.id})` : ""} 칸` : `${id ?? "?"} 칸`;
  }

  // ------------------------------------------------------------------ 파라미터 표시 정보 (한글 라벨 · 입력기 종류 · 도움말)
  const DIRS = ["UP", "DOWN", "LEFT", "RIGHT", "UL", "UR", "DL", "DR"];
  const PARAM_META = {
    tex: ["수식", "tex", "LaTeX. $ 없이 써도 됩니다"], text: ["글", "text", "한글 설명. 수식은 $…$ 안에"], lines: ["줄 목록", "lines", "한 줄에 하나씩. 순서대로 한 줄씩 적힙니다"],
    title: ["제목", "title"], subtitle: ["부제", "subtitle"], tag: ["태그", "tag", "예: 수학Ⅰ"], id: ["이름 (id)", "id", "나중에 강조·지우기·카메라에서 이 이름으로 가리킵니다"],
    ids: ["대상 이름들", "ids", "쉼표로 여러 개"], keep: ["남길 이름들", "keep"], section: ["칠판 칸", "section"], color: ["색", "color"], label: ["라벨(수식)", "label"],
    expr: ["식  y = …", "expr", "파이썬 문법: x**2, exp(x), log(x), sin(x)"], x_range: ["x 범위", "x_range", "최소, 최대[, 눈금]"], y_range: ["y 범위", "y_range", "최소, 최대[, 눈금]"],
    pos: ["좌표 (x, y)", "pos"], choices: ["보기 ①~⑤", "choices", "한 줄에 하나씩"], index: ["줄 번호", "index", "0 이 첫 줄"], choice: ["정답 보기 번호", "choice", "1~5"],
    mode: ["강조 방식", "mode"], seconds: ["초", "seconds"], fn: ["함수 이름", "fn", "프로젝트 폴더 hooks.py 에 def 로 정의한 함수"], ko: ["한글 포함", "ko", "한글이 섞여 있으면 켜세요 (xelatex)"],
    box: ["상자 치기", "box"], underline: ["밑줄", "underline"], scale: ["크기 배율", "scale"], width: ["폭", "width"], height: ["높이", "height"], indent: ["들여쓰기", "indent"], space: ["위 여백", "space"],
    opacity: ["불투명도", "opacity", "0(투명)~1"], out: ["사라짐", "out", "끄면 반대로 나타남"], dashed: ["점선", "dashed"], stroke_width: ["선 굵기", "stroke_width"], slope: ["기울기", "slope"], intercept: ["y절편", "intercept"],
    through: ["지나는 두 점", "through", "JSON: [[x1,y1],[x2,y2]]"], a: ["시작점", "a", "점 이름 또는 x, y"], b: ["끝점", "b", "점 이름 또는 x, y"], point: ["점 이름", "point"], source: ["원본 이름", "source"],
    dx: ["x 이동량", "dx"], dy: ["y 이동량", "dy"], items: ["점 목록", "items", "JSON: [{id, at:[x,y], label}]"], of: ["어느 식 전개", "of", "derive 의 이름(id)"], parts: ["조각", "parts"], why: ["이유", "why"],
    caption_text: ["설명", "caption_text"], position: ["위치", "position"], board: ["보드 포함", "board"], overview: ["이동 중 전체 보기", "overview"], focus: ["초점 대상", "focus", "이름(id)"], reset: ["기본 뷰로", "reset"],
    sections: ["보이게 할 칸들", "sections", "쉼표로 여러 개"], pad: ["여백", "pad"], grid: ["격자", "grid"], numbers: ["눈금 숫자", "numbers"], equal_aspect: ["가로세로 같은 비율", "equal_aspect"], labels: ["축 라벨", "labels"],
    center: ["중심 좌표", "center"], radius: ["점 크기", "radius"], flash: ["반짝", "flash"], coords_label: ["좌표 표시", "coords_label"], label_dir: ["라벨 방향", "label_dir"], label_scale: ["라벨 크기", "label_scale"], label_at: ["라벨 위치 x", "label_at"],
    smooth: ["부드럽게", "smooth"], fill_opacity: ["채움 정도", "fill_opacity"], closed: ["닫힌 도형", "closed"], points: ["점들", "points", "점 이름들 또는 JSON"], near: ["가까운 대상", "near"], dir: ["방향", "dir"], bg: ["배경", "bg"], buff: ["간격", "buff"],
    x_label: ["x 라벨", "x_label"], y_label: ["y 라벨", "y_label"], show_perpendicular: ["수선 표시", "show_perpendicular"], guide_color: ["보조선 색", "guide_color"], keep_guide: ["보조선 남김", "keep_guide"], right_angle: ["직각 표시", "right_angle"],
    arrow: ["화살표", "arrow"], arrow_label: ["화살표 라벨", "arrow_label"], keep_source: ["원본 남김", "keep_source"], x: ["x 값", "x"], lag: ["점 사이 간격(초)", "lag"], dim_opacity: ["흐림 정도", "dim_opacity"], line_buff: ["줄 간격", "line_buff"],
    t2c: ["부분 색", "t2c", 'JSON: {"x": "q1"}'], plain: ["일반 글꼴", "plain"], animation: ["애니메이션", "animation"], keep_header: ["헤더 유지", "keep_header"], accent: ["강조색", "accent"], why_color: ["이유 색", "why_color"], keep_color: ["색 유지", "keep_color"],
  };
  const SELECT_OPTIONS = {
    mode: Object.keys(MODE_KO).map((k) => [k, MODE_KO[k]]), position: [["bottom", "아래"], ["top", "위"]], animation: [["write", "써 내려가기"], ["fade", "서서히"]],
    label_dir: DIRS.map((d) => [d, d]), dir: DIRS.map((d) => [d, d]),
  };
  const MATH_KEYS = new Set(["tex", "text", "lines", "label", "choices", "why", "x_label", "y_label", "arrow_label", "caption_text", "subtitle", "title"]);
  const PLAIN_TEXT_ACTS = new Set(["title_card", "end_card", "section", "board_title"]);   // title/text 가 수식 아님
  function paramLabel(doName, key) { const m = PARAM_META[key]; return m ? m[0] : key; }
  function paramHint(key) { const m = PARAM_META[key]; return m && m[2] ? m[2] : ""; }
  /** 입력기 종류 결정: 값 → 카탈로그 타입 → 키 이름. */
  function paramKind(act, key, pspec) {
    const val = act[key];
    if (key === "color" || key === "guide_color" || key === "accent" || key === "why_color") return "color";
    if (key === "section") return "section";
    if (SELECT_OPTIONS[key]) return "select";
    if (key === "fn") return "fn";
    const t = pspec?.type || "";
    if (typeof val === "boolean" || t === "bool" || /^bool/.test(t)) return "bool";
    if (typeof val === "number" || /^(float|int)/.test(t)) return "num";
    if (key === "lines" || key === "choices") return "lines";
    if (key === "ids" || key === "keep" || key === "sections" || key === "points" && Array.isArray(val) && val.every((v) => typeof v === "string")) return "csv";
    if (key === "pos" || key === "center" || key === "x_range" || key === "y_range" || key === "a" || key === "b" || key === "focus" && Array.isArray(val)) return "nums";
    if (Array.isArray(val) && val.every((v) => typeof v === "number")) return "nums";
    if (val !== undefined && typeof val === "object") return "json";
    if (/^dict/.test(t) || /^list\[dict/.test(t) || key === "through") return "json";
    if (/^list/.test(t) && val === undefined) return key === "lines" || key === "choices" ? "lines" : "csv";
    return "text";
  }

  // ------------------------------------------------------------------ 렌더된 영상에서 장면 대표 화면 뽑기 (브라우저 안에서, ffmpeg 불필요)
  const thumbs = { cache: new Map(), queue: [], busy: false, video: null, canvas: null };
  function renderedSource() {
    const o = state.outputs || {}; const full = o.full || {}, part = o.partial || {};
    if ((full.final || full.preview) && full.timeline) return { url: full.final || full.preview, timeline: full.timeline, kind: full.final ? "final" : "preview" };
    if ((part.preview || part.final) && part.timeline) return { url: part.preview || part.final, timeline: part.timeline, kind: "partial" };
    return null;
  }
  function renderedRange(seg) {
    const src = renderedSource(); if (!src) return null;
    const s = (src.timeline.segments || []).find((x) => x.id === seg.id);
    if (!s) return null;
    return { start: s.start, end: s.end, stale: normNarr(s.narration) !== normNarr(seg.narration), url: src.url, kind: src.kind };
  }
  function grabFrame(url, t) {
    const key = `${url}@${t.toFixed(2)}`;
    if (thumbs.cache.has(key)) return Promise.resolve(thumbs.cache.get(key));
    return new Promise((resolve) => { thumbs.queue.push({ url, t, key, resolve }); pumpThumbs(); });
  }
  async function pumpThumbs() {
    if (thumbs.busy || !thumbs.queue.length) return;
    thumbs.busy = true;
    const job = thumbs.queue.shift();
    try {
      if (!thumbs.video) { thumbs.video = el("video", { muted: "", preload: "auto", style: "position:fixed;left:-9999px;width:320px" }); document.body.append(thumbs.video); thumbs.canvas = el("canvas"); }
      const v = thumbs.video;
      if (v.getAttribute("src") !== job.url) {
        v.src = job.url;
        await new Promise((ok, bad) => { v.onloadedmetadata = ok; v.onerror = () => bad(new Error("video load")); });
      }
      v.currentTime = Math.min(job.t, Math.max(0, (v.duration || job.t) - 0.05));
      await new Promise((ok, bad) => { v.onseeked = ok; v.onerror = () => bad(new Error("seek")); setTimeout(() => bad(new Error("seek timeout")), 8000); });
      const c = thumbs.canvas; c.width = 320; c.height = Math.round(320 * (v.videoHeight || 9) / (v.videoWidth || 16));
      c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
      const data = c.toDataURL("image/jpeg", 0.72);
      thumbs.cache.set(job.key, data); job.resolve(data);
    } catch (_) { job.resolve(null); }
    thumbs.busy = false;
    pumpThumbs();
  }
  function thumbImg(seg, cls, ratio = 0.72) {
    const r = renderedRange(seg); if (!r) return null;
    const img = el("img", { class: cls + (r.stale ? " stale" : ""), alt: "", title: r.stale ? "대본이 바뀐 뒤 아직 렌더하지 않았습니다 (이전 렌더 화면)" : `${fmtClock(r.start)} – ${fmtClock(r.end)}` });
    grabFrame(r.url, r.start + (r.end - r.start) * ratio).then((d) => { if (d) img.src = d; else img.remove(); });
    return img;
  }
  function activeSection(segIndex) {
    const secs = state.doc.layout?.chalk?.sections || [];
    if (!secs.length) return null;
    let cur = null;
    for (let i = 0; i < segIndex; i++) {
      for (const a of state.doc.segments[i]?.actions || []) if (a.do === "goto" && a.section) cur = a.section;
    }
    const visits = [];
    for (const a of state.doc.segments[segIndex]?.actions || []) if (a.do === "goto" && a.section) visits.push(a.section);
    const path = [cur ?? secs[0].id, ...visits].filter((v, k, arr) => k === 0 || arr[k - 1] !== v);
    const last = path[path.length - 1];
    const s = secs.find((x) => x.id === last);
    return { id: last, path, layout: s?.layout || "?", title: s?.title, moved: visits.length > 0, missing: !s };
  }
  function playRange(seg) {
    const r = renderedRange(seg); if (!r) return;
    playSpan(r.url, r.start, r.end);
  }
  function playSpan(url, start, end) {
    const video = $("#video"); const vs = $("#videoSource");
    const opt = [...vs.options].find((o) => o.dataset.url === url);
    if (opt && vs.value !== opt.value) { vs.value = opt.value; video.src = url; }
    switchTab("video");
    const go = () => { video.currentTime = Math.max(0, start); video.play().catch(() => {}); };
    if (video.readyState >= 1) go(); else video.addEventListener("loadedmetadata", go, { once: true });
    if (video._stopSpan) video.removeEventListener("timeupdate", video._stopSpan);
    const stop = () => { if (video.currentTime >= end - 0.05) { video.pause(); video.removeEventListener("timeupdate", stop); } };
    video._stopSpan = stop;
    video.addEventListener("timeupdate", stop);
  }

  // ------------------------------------------------------------------ 동작 하나가 영상의 어느 구간인지
  const DEFAULT_DUR = {
    goto: 1.8, title_card: 1.6, end_card: 2.4, problem: 2.0, problem_focus: 0.6, problem_dock: 1.0, write: 1.2, caption: 0.5,
    step: 2.0, axes: 1.2, plot: 1.2, line: 0.9, vline: 0.5, point: 0.6, points: 1.0, polygon: 1.0, segment: 0.9, arrow: 0.9,
    guides: 0.8, reflect: 1.6, translate_copy: 1.8, highlight: 0.9, dim: 0.5, undim: 0.5, fade: 0.6, camera: 1.2, custom: 2.5,
    answer: 1.2, label: 0.6, clear: 0.8, section: 1.0, space: 0.0, board_init: 1.0, board_write: 1.0, board_replace: 1.0,
    board_highlight: 0.8, board_clear: 0.6, board_title: 0.8,
  };
  function actionDuration(a) {
    if (a.do === "wait") return Number(a.seconds ?? 1);
    if (a.do === "derive") { const st = a.steps || []; return st.reduce((s, x) => s + Number(x.run_time ?? a.run_time ?? 2.0), 0) + 0.4; }
    return Number(a.run_time ?? DEFAULT_DUR[a.do] ?? 1.0);
  }
  function actionSpans(seg) {
    const rr = renderedRange(seg); if (!rr || rr.stale) return null;
    const src = renderedSource();
    const o = state.outputs || {}; const bag = src.kind === "partial" ? (o.partial || {}) : (o.full || {});
    const log = Array.isArray(bag.actions_log) ? bag.actions_log.filter((x) => x.segment === seg.id) : [];
    if (log.length === seg.actions.length && log.every((x, k) => x.action === seg.actions[k].do)) {
      return { url: rr.url, exact: true, spans: log.map((x) => ({ start: x.start, end: x.end })) };
    }
    const info = sentencesFor(seg); if (!info.exact) return null;
    const S = rr.start, E = rr.end;
    const resolveAt = (at) => {
      if (typeof at === "number") return S + at;
      if (typeof at === "string" && /^s\d+$/.test(at)) { const s = info.list[Number(at.slice(1)) - 1]; return s ? S + s.start : null; }
      return null;
    };
    let t = S; const spans = [];
    for (const a of seg.actions) {
      let start = t;
      const atT = resolveAt(a.at);
      if (atT !== null) start = Math.max(t, atT);
      start = Math.min(start, E);
      let end;
      if (a.do === "derive" && (a.steps || []).length) {
        let ts = start;
        for (const st of a.steps) { const sa = resolveAt(st.at); if (sa !== null) ts = Math.max(ts, sa); ts = Math.min(E, ts + Number(st.run_time ?? a.run_time ?? 2.0)); }
        end = Math.min(E, ts + 0.3);
      } else end = Math.min(E, start + actionDuration(a));
      spans.push({ start, end }); t = end;
    }
    return { url: rr.url, exact: false, spans };
  }
  function sectionBefore(segIndex, actIndex) {
    let cur = null;
    for (let i = 0; i < segIndex; i++) for (const a of state.doc.segments[i]?.actions || []) if (a.do === "goto" && a.section) cur = a.section;
    const acts = state.doc.segments[segIndex]?.actions || [];
    for (let k = 0; k < actIndex; k++) if (acts[k].do === "goto" && acts[k].section) cur = acts[k].section;
    return cur ?? (state.doc.layout?.chalk?.sections?.[0]?.id ?? null);
  }
  function boardMap(fromId, toId, extraIds = []) {
    const secs = state.doc.layout?.chalk?.sections || [];
    if (!secs.length) return null;
    const map = el("div", { class: "boardmap" });
    secs.forEach((s) => {
      const isTo = s.id === toId, isFrom = s.id === fromId && !isTo, isExtra = extraIds.includes(s.id);
      const inner = s.layout === "split"
        ? el("div", { class: "bm-split" }, el("i", { class: "bm-graph" }), el("i", { class: "bm-lines" }))
        : el("div", { class: "bm-full" }, el("i", { class: "bm-lines" }));
      map.append(el("div", { class: "bsec" + (isTo ? " to" : "") + (isFrom ? " from" : "") + (isExtra ? " extra" : ""), title: `${s.id}${s.title ? " — " + s.title : ""} (${s.layout || "full"})` },
        el("div", { class: "bm-title" }, s.title || s.id), inner,
        el("div", { class: "bm-id" }, s.id),
        isTo ? el("div", { class: "bm-tag" }, fromId && fromId !== toId ? "→ 여기로" : "여기") : isFrom ? el("div", { class: "bm-tag from" }, "지금") : null));
    });
    return map;
  }
  function actionPreview(seg, act, i) {
    const box = el("div", { class: "apreview" });
    const segIndex = state.doc.segments.indexOf(seg);
    const sp = actionSpans(seg);
    const info = sentencesFor(seg);
    let when;
    if (typeof act.at === "string" && /^s\d+$/.test(act.at)) {
      const s = info.list[Number(act.at.slice(1)) - 1];
      when = s ? `${act.at.slice(1)}번째 문장이 시작될 때${s.start !== undefined ? ` (${s.start.toFixed(1)}s)` : ""}: “${short(s.text, 40)}”` : `${act.at.slice(1)}번째 문장 — 이 장면에는 그런 문장이 없습니다`;
    } else if (typeof act.at === "number") when = `장면 시작 ${act.at}초 뒤`;
    else when = i === 0 ? "장면이 시작되자마자" : `앞 동작(${actLabel(seg.actions[i - 1].do)})이 끝난 직후 이어서`;
    const dur = sp ? sp.spans[i].end - sp.spans[i].start : actionDuration(act);
    box.append(el("div", { class: "when" }, el("b", {}, "언제"), ` ${when}`, el("span", { class: "hint" }, ` · 약 ${dur.toFixed(1)}초 동안${!sp && act.run_time === undefined && act.do !== "wait" ? " (기본값)" : ""}`)));

    if (sp) {
      const { start, end } = sp.spans[i];
      const before = el("img", { class: "frame", alt: "" }), after = el("img", { class: "frame", alt: "" });
      const rr = renderedRange(seg);
      grabFrame(sp.url, Math.max(rr.start, start - 0.08)).then((d) => { if (d) before.src = d; });
      grabFrame(sp.url, Math.min(rr.end - 0.05, end + 0.15)).then((d) => { if (d) after.src = d; });
      const play = () => playSpan(sp.url, Math.max(rr.start, start - 0.3), end + 0.4);
      box.append(el("div", { class: "frames2" },
        el("figure", { onclick: play, title: "이 동작 구간 재생" }, before, el("figcaption", {}, `실행 전 ${fmtClock(start)}`)),
        el("span", { class: "arr" }, "➜"),
        el("figure", { onclick: play, title: "이 동작 구간 재생" }, after, el("figcaption", {}, `실행 후 ${fmtClock(end)}`)),
        el("div", { class: "side" },
          el("button", { class: "mini", onclick: play }, "▶ 이 동작만 재생"),
          el("span", { class: "hint" }, sp.exact ? "렌더 로그 기준 정확한 구간" : "시작 시점·길이로 추정한 구간"))));
    } else {
      const rr = renderedRange(seg);
      box.append(el("p", { class: "hint" }, rr && rr.stale ? "대본이 바뀐 뒤 아직 렌더하지 않아 실행 전/후 화면을 보여 줄 수 없습니다. 상단 ‘① 이 장면 미리보기’ 를 누르세요."
        : rr ? "문장 시각 정보가 없어 실행 전/후 화면을 잡을 수 없습니다 (대본의 ▶ 듣기 버튼을 눌러 보세요)."
        : "아직 렌더한 적이 없어 실행 전/후 화면이 없습니다. 상단 ‘① 이 장면 미리보기’ 를 누르면 여기에 나타납니다."));
    }

    if (act.do === "goto" || (act.do === "camera" && (act.sections || act.reset || act.focus))) {
      const from = sectionBefore(segIndex, i);
      const to = act.do === "goto" ? act.section : act.reset ? from : (typeof act.focus === "string" ? act.focus : null);
      const extra = act.do === "camera" && Array.isArray(act.sections) ? act.sections : [];
      const map = boardMap(from, to, extra);
      if (map) box.append(el("div", { class: "mapwrap" },
        el("div", { class: "hint" }, act.do === "goto" ? `카메라가 ‘${from ?? "?"}’ 칸에서 ‘${to ?? "?"}’ 칸으로 옮겨 갑니다. 칠판은 왼쪽→오른쪽으로 이어진 칸들입니다.` : act.reset ? "카메라를 현재 칸 전체가 보이는 기본 뷰로 되돌립니다." : extra.length ? `칸 ${extra.join(" ~ ")} 가 모두 보이게 줌아웃합니다.` : "카메라 이동"),
        map));
    }
    return box;
  }

  // ------------------------------------------------------------------ 장면 목록
  function segDuration(seg) {
    const info = state.sentences[seg.id];
    if (info && info.exact && info.narr === normNarr(seg.narration) && info.sentences.length) return info.sentences[info.sentences.length - 1].end;
    return null;
  }
  function renderSegList() {
    const ul = $("#segList");
    ul.innerHTML = "";
    if (!state.doc.segments.length) {
      ul.append(el("li", { class: "side-empty", style: "cursor:default;display:block" }, "장면이 없습니다.", el("br"), "위의 ＋ 장면 버튼으로 첫 장면을 만들어 보세요."));
      return;
    }
    let t0 = Number(state.doc.meta?.intro_silence ?? 0.6);
    state.doc.segments.forEach((seg, i) => {
      const acts = seg.actions || [];
      const dur = segDuration(seg);
      const nS = sentencesFor(seg).list.length;
      const bar = el("div", { class: "mix" });
      for (const a of acts) bar.append(el("i", { style: `background:${actColor(a.do)}`, title: `${actLabel(a.do)} ${summarize(a)}` }));
      // 슬라이드 썸네일: 편집 내용을 바로 반영하는 무대 축소판 (없으면 렌더 프레임)
      let thumb = null;
      if (window.StudioStage) { try { thumb = window.StudioStage.thumbnail(state.doc, i, 196); } catch (_) { thumb = null; } }
      if (!thumb) thumb = thumbImg(seg, "thumb");
      const first = splitSentences(seg.narration)[0];
      const li = el("li", { class: i === state.sel ? "on" : "", draggable: "true", onclick: () => selectSegment(i), title: "클릭: 이 장면 편집 · 드래그: 순서 바꾸기" },
        el("span", { class: "n" }, String(i + 1)),
        el("div", { class: "body" },
          el("div", { class: "id" }, seg.id || "(이름 없음)"),
          first ? el("div", { class: "first" }, first) : null,
          el("div", { class: "meta" }, `${nS}문장 · ${acts.length}동작` + (dur !== null ? ` · ${dur.toFixed(0)}초` : "")),
          thumb,
          bar),
        dur !== null ? el("span", { class: "t0" }, fmtClock(t0)) : null);
      if (dur !== null) t0 += dur + Number(seg.pad ?? state.doc.meta?.segment_pad ?? 0.5);
      li.addEventListener("dragstart", (e) => { e.dataTransfer.setData("text/plain", String(i)); });
      li.addEventListener("dragover", (e) => { e.preventDefault(); li.classList.add("dragover"); });
      li.addEventListener("dragleave", () => li.classList.remove("dragover"));
      li.addEventListener("drop", (e) => {
        e.preventDefault(); li.classList.remove("dragover");
        const from = Number(e.dataTransfer.getData("text/plain"));
        if (from === i) return;
        const [m] = state.doc.segments.splice(from, 1);
        state.doc.segments.splice(i, 0, m);
        state.sel = i; touched(); renderSegList(); renderSegEditor();
      });
      ul.append(li);
    });
  }
  const fmtClock = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  function selectSegment(i) { if (i !== state.sel) state.cursor = { seg: i, act: null }; state.sel = i; showPane("seg"); renderSegList(); renderSegEditor(); }
  state.selectSegment = selectSegment;

  // ------------------------------------------------------------------ 장면 편집기
  function renderSegEditor() {
    const pane = $("#segEditor");
    pane.innerHTML = "";
    const seg = state.doc.segments[state.sel];
    if (!seg) {
      pane.append(el("div", { class: "empty" },
        el("div", { class: "big" }, "🎞"),
        el("p", {}, el("b", {}, "장면"), "은 영상의 한 토막입니다. 장면마다 ", el("b", {}, "대본(내레이션)"), "을 쓰고, 그 문장에 맞춰 칠판에 일어날 ", el("b", {}, "동작"), "을 붙입니다."),
        el("p", { class: "hint" }, "예: “함수 f 의 그래프를 그려 봅시다” 라는 문장에 ‘함수 그래프’ 동작을 붙이면, 그 문장을 읽을 때 그래프가 그려집니다."),
        el("div", { class: "actions" },
          el("button", { class: "accent", onclick: () => addSegment() }, "＋ 첫 장면 만들기"),
          el("button", { class: "ghost", onclick: showHelp }, "? 사용법 보기"))));
      return;
    }
    seg.actions = seg.actions || [];

    const idIn = el("input", { class: "seg-id", value: seg.id || "", placeholder: "장면 이름 (예: read_problem)", spellcheck: "false", title: "장면 이름 — 영문/숫자/밑줄. 렌더 결과 파일과 타임라인에 이 이름으로 표시됩니다" });
    idIn.addEventListener("change", () => { seg.id = idIn.value.trim(); touched(); renderSegList(); });
    const padIn = el("input", { class: "seg-pad", value: seg.pad ?? "", placeholder: `뒤 여백 ${state.doc.meta?.segment_pad ?? 0.5}s`, title: "이 장면 뒤에 쉬는 시간(초). 비우면 영상 설정의 기본값" });
    padIn.addEventListener("change", () => { const n = parseVal(padIn.value); if (n === undefined) delete seg.pad; else seg.pad = n; touched(); });
    const dur = segDuration(seg);
    const sec = activeSection(state.sel);
    const secBadge = sec ? el("span", { class: "sec-badge" + (sec.missing ? " bad" : ""), title: sec.missing ? "영상 설정의 칠판 칸 목록에 없는 칸입니다" : (sec.moved ? "이 장면에서 칠판 칸을 옮겨 갑니다 (시작 칸 → 이동한 칸)" : "앞 장면에서 이어지는 칠판 칸 (이 장면에는 칸 이동이 없음)") },
      "칠판 칸 ", el("b", {}, sec.path.join(" → ")), ` · ${sec.layout === "split" ? "그림+판서" : sec.layout === "full" ? "판서 전체" : sec.layout}`, sec.title ? el("span", { class: "ttl" }, ` “${sec.title}”`) : null) : null;
    const head = el("div", { class: "seg-head" },
      el("span", { class: "badge" }, String(state.sel + 1)),
      el("div", { class: "titles" }, idIn,
        el("div", { class: "hint" }, `${state.sel + 1} / ${state.doc.segments.length} 번째 장면` + (dur !== null ? ` · 대본 ${dur.toFixed(1)}초` : "") + ` · 동작 ${seg.actions.length}개`),
        secBadge),
      padIn,
      el("span", { class: "spacer" }),
      el("span", { class: "tools" },
        el("button", { class: "ghost mini", title: "앞으로", onclick: () => moveSeg(-1) }, "↑"),
        el("button", { class: "ghost mini", title: "뒤로", onclick: () => moveSeg(1) }, "↓"),
        el("button", { class: "ghost mini", title: "이 장면을 복제해 바로 뒤에 추가", onclick: () => dupSeg() }, "복제"),
        el("button", { class: "danger mini", onclick: () => delSeg() }, "삭제")));
    pane.append(head);

    // 0) 무대: 편집 즉시 그려 보는 미리보기 (기본) / 실제 렌더 화면
    const rr = renderedRange(seg);
    const shot = el("section", { class: "block shots stagebox" });
    const modeBtns = el("span", { class: "modes" },
      el("button", { class: state.stageMode !== "render" ? "on" : "", onclick: () => { state.stageMode = "stage"; renderSegEditor(); } }, "즉시 미리보기"),
      el("button", { class: state.stageMode === "render" ? "on" : "", onclick: () => { state.stageMode = "render"; renderSegEditor(); }, title: rr ? "마지막 렌더에서 뽑은 실제 화면" : "아직 렌더한 적이 없습니다" }, "렌더 화면" + (rr ? "" : " (없음)")));
    if (state.stageMode === "render" && rr) {
      const frames = el("div", { class: "frames" });
      [["시작", 0.04], ["중간", 0.5], ["끝", 0.96]].forEach(([lab, ratio]) => {
        const img = thumbImg(seg, "frame", ratio);
        frames.append(el("figure", { onclick: () => playRange(seg), title: "클릭하면 오른쪽 영상 패널에서 이 구간을 재생" }, img, el("figcaption", {}, lab)));
      });
      shot.append(el("div", { class: "block-head" }, el("h3", {}, "화면"), modeBtns,
        el("span", { class: "hint" }, `${rr.kind === "final" ? "최종" : rr.kind === "preview" ? "프리뷰" : "부분"} 렌더 ${fmtClock(rr.start)} – ${fmtClock(rr.end)}` + (rr.stale ? " · 대본이 바뀐 뒤 렌더 안 함" : "")),
        el("span", { class: "spacer" }),
        el("button", { class: "mini", onclick: () => playRange(seg) }, "▶ 이 구간 재생"),
        el("button", { class: "ghost mini", title: "이 장면만 480p 로 다시 렌더", onclick: () => startBuild("partial") }, "다시 렌더")), frames);
      if (rr.stale) shot.classList.add("stale");
      state.renderStage = null;
    } else {
      if (state.stageMode === "render") state.stageMode = "stage";
      const host = el("div", { class: "stage-host" });
      const strip = el("div", { class: "steps-strip" });
      shot.append(el("div", { class: "block-head" }, el("h3", {}, "무대"), modeBtns,
        el("span", { class: "hint" }, "이 장면이 끝났을 때의 칠판. 노란 테두리 = 지금 편집하는 동작 · 흐린 것 = 아직 안 나온 동작 · 무대의 글씨·그래프를 클릭하면 그 카드가 열립니다"),
        el("span", { class: "spacer" }),
        el("button", { class: "ghost mini", title: "이 장면만 480p 로 실제 렌더 (수십 초)", onclick: () => startBuild("partial") }, rr ? "다시 렌더" : "① 이 장면 미리보기")), host, strip,
        el("div", { class: "legend" }, el("span", {}, el("i", { style: "background:#ffd23f" }), "편집 중"), el("span", {}, el("i", { style: "background:#f2f2e6" }), "이 장면에서 나온 것"), el("span", {}, el("i", { style: "background:#8b93a7" }), "앞 장면에서 이미 있던 것"), el("span", {}, el("i", { style: "background:#3a4256" }), "아직 안 나온 것"),
          el("span", { class: "spacer" }), el("span", {}, "실제 렌더와 배치가 조금 다를 수 있어요")));
      state.renderStage = () => renderStage(host, strip, seg);
      setTimeout(state.renderStage, 0);
    }
    pane.append(shot);

    // 1) 대본
    const narr = el("section", { class: "block narr" });
    const ta = el("textarea", { placeholder: "여기에 말할 내용을 쓰세요. 마침표(.)·물음표(?)로 문장을 끊으면, 아래 ②에서 문장마다 동작을 붙일 수 있습니다." });
    ta.value = seg.narration || "";
    const audio = el("audio", { controls: "", class: "hidden", style: "height:28px" });
    const btnTts = el("button", { class: "ghost mini", title: "목소리로 합성해 들어 보고, 문장별 실제 시각을 재서 ②에 반영합니다", onclick: async () => {
      btnTts.disabled = true; btnTts.textContent = "합성 중…";
      try {
        const r = await api("/api/tts", { method: "POST", body: { text: ta.value, voice: seg.voice || state.doc.meta.voice || "ko-KR-InJoonNeural", rate: seg.rate || state.doc.meta.rate || "+0%" } });
        state.sentences[seg.id] = { exact: true, sentences: r.sentences, narr: normNarr(ta.value) };
        audio.src = r.audio_url; audio.classList.remove("hidden"); audio.play().catch(() => {});
        toast(`대본 ${r.duration.toFixed(1)}초, ${r.sentences.length}문장`);
        renderSync(); renderCards(); renderSegList();
      } catch (e) { toast(e.message, "bad"); }
      btnTts.disabled = false; btnTts.textContent = "▶ 듣기 · 문장 시간 재기";
    } }, "▶ 듣기 · 문장 시간 재기");
    narr.append(el("div", { class: "block-head" }, el("h3", {}, "① 대본 (내레이션)"), el("span", { class: "hint" }, "이 글을 목소리가 읽습니다"), el("span", { class: "spacer" }), audio, btnTts), ta);
    ta.addEventListener("input", () => { seg.narration = ta.value; touched("narr:" + state.sel); renderSync(); });
    pane.append(narr);

    // 2) 문장 ↔ 동작
    const sync = el("section", { class: "block syncb" });
    pane.append(sync);
    const renderSync = () => { sync.innerHTML = ""; sync.append(syncBoard(seg, (idx) => focusCard(idx), (at) => openPalette(seg, { at }))); };

    // 3) 동작 카드
    const cardsBox = el("div", { class: "cards" });
    const acts = el("section", { class: "block" },
      el("div", { class: "block-head" }, el("h3", {}, `③ 동작 ${seg.actions.length}개`),
        el("span", { class: "hint" }, "위에서 아래 순서로 실행 · 카드를 누르면 세부 설정"), el("span", { class: "spacer" }),
        el("button", { class: "ghost mini", onclick: () => { seg.actions.forEach((a) => state.expanded.add(a)); renderCards(); } }, "모두 펼치기"),
        el("button", { class: "ghost mini", onclick: () => { state.expanded.clear(); renderCards(); } }, "모두 접기"),
        el("button", { class: "accent mini", onclick: () => openPalette(seg, {}) }, "＋ 동작 추가")),
      cardsBox);
    pane.append(acts);
    const renderCards = () => {
      cardsBox.innerHTML = "";
      if (!seg.actions.length) {
        cardsBox.append(el("div", { class: "empty" }, el("p", {}, "이 장면에는 아직 동작이 없습니다 — 대본만 읽힙니다."),
          el("p", { class: "hint" }, "‘＋ 동작 추가’ 로 판서·그래프·식 전개 같은 동작을 넣거나, ②의 문장 줄에서 ‘＋ 여기서’ 를 눌러 그 문장에 맞춰 넣을 수 있습니다."),
          el("div", { class: "actions" }, el("button", { class: "accent", onclick: () => openPalette(seg, {}) }, "＋ 동작 추가"))));
        return;
      }
      seg.actions.forEach((act, i) => cardsBox.append(actionCard(seg, act, i)));
    };
    function focusCard(idx, noScroll = false) {
      const act = seg.actions[idx]; if (!act) return;
      state.cursor = { seg: state.sel, act: idx };
      state.expanded.add(act); renderCards();
      state.renderStage?.();
      const c = cardsBox.children[idx]; if (!c) return;
      if (!noScroll) c.scrollIntoView({ behavior: "smooth", block: "center" });
      c.classList.add("flash"); setTimeout(() => c.classList.remove("flash"), 1200);
    }
    state.focusCard = focusCard;
    renderSync(); renderCards();
  }

  // ------------------------------------------------------------------ 무대 (즉시 미리보기) 그리기
  /** 커서 동작이 실행될 때 읽히는 문장 (자막 띠용). */
  function subtitleFor(seg, actIdx) {
    const list = sentencesFor(seg).list; if (!list.length) return "";
    const acts = seg.actions || [];
    let at = null;
    for (let k = (actIdx === null ? acts.length - 1 : actIdx); k >= 0; k--) { const a = acts[k]?.at; if (a !== undefined && a !== null && a !== "") { at = a; break; } }
    if (typeof at === "string" && /^s\d+$/.test(at)) return list[Math.min(list.length, Number(at.slice(1))) - 1]?.text || "";
    if (typeof at === "number" && list[0]?.start !== undefined) { const s = list.find((x) => at < x.end); return (s || list[list.length - 1]).text; }
    return actIdx === null ? list[list.length - 1].text : list[0].text;
  }
  function renderStage(host, strip, seg) {
    if (!window.StudioStage || !state.doc) return;
    const cursor = { seg: state.sel, act: state.cursor.seg === state.sel ? state.cursor.act : null };
    try {
      window.StudioStage.render(host, state.doc, { cursor, subtitle: subtitleFor(seg, cursor.act), onPick: (si, ai) => { if (si !== state.sel) { selectSegment(si); setTimeout(() => state.focusCard?.(ai), 60); } else state.focusCard?.(ai); } });
    } catch (e) { host.innerHTML = ""; host.append(el("p", { class: "hint", style: "padding:12px" }, "무대를 그리지 못했습니다: " + e.message)); }
    // 동작 단계 스트립 (파워포인트의 애니메이션 창처럼)
    strip.innerHTML = "";
    const acts = seg.actions || [];
    const go = (i) => { state.cursor = { seg: state.sel, act: i }; if (i !== null) state.focusCard?.(i, true); else { state.renderStage?.(); } };
    strip.append(el("button", { class: "ghost mini nav", title: "앞 동작", onclick: () => go(cursor.act === null ? Math.max(0, acts.length - 1) : Math.max(0, cursor.act - 1)) }, "◀"));
    acts.forEach((a, i) => {
      const rel = cursor.act === null ? "done" : i < cursor.act ? "done" : i === cursor.act ? "on" : "";
      strip.append(el("button", { class: "stp " + rel, style: `--c:${actColor(a.do)}`, title: `${actLabel(a.do)} — ${summarize(a)}\n이 동작까지 실행된 무대를 봅니다`, onclick: () => go(i) }, el("b", {}, String(i + 1)), actLabel(a.do)));
    });
    strip.append(el("button", { class: "ghost mini nav", title: "다음 동작", onclick: () => go(cursor.act === null ? null : cursor.act + 1 >= acts.length ? null : cursor.act + 1) }, "▶"));
    strip.append(el("button", { class: "stp " + (cursor.act === null ? "on" : ""), title: "장면이 끝났을 때", onclick: () => go(null) }, "끝"));
    if (!acts.length) strip.append(el("span", { class: "hint" }, "동작을 추가하면 여기서 한 단계씩 넘겨 볼 수 있습니다"));
  }

  /** 문장(줄) ↔ 동작(칩) 표 + 비율 시간 바. */
  function syncBoard(seg, onPick, onAddAt) {
    const info = sentencesFor(seg);
    const sents = info.list;
    const total = info.exact && sents.length ? sents[sents.length - 1].end : null;
    const rows = sents.map((s) => ({ s, acts: [] }));
    const before = { s: null, acts: [] }, numeric = [];
    let cur = rows.length ? 0 : -1, curNumeric = null;
    seg.actions.forEach((a, i) => {
      const at = a.at;
      if (typeof at === "string" && /^s\d+$/.test(at)) {
        const k = Number(at.slice(1)) - 1;
        cur = Math.min(Math.max(k, 0), rows.length - 1); curNumeric = null;
        if (k >= rows.length) { (rows[rows.length - 1] || before).acts.push({ a, i, warn: true }); return; }
      } else if (typeof at === "number") {
        if (total !== null) { const k = sents.findIndex((s) => at < s.end); cur = k < 0 ? rows.length - 1 : k; curNumeric = null; }
        else { curNumeric = at; }
      }
      if (curNumeric !== null) { let r = numeric.find((x) => x.t === curNumeric); if (!r) { r = { t: curNumeric, acts: [] }; numeric.push(r); } r.acts.push({ a, i }); return; }
      (cur >= 0 ? rows[cur] : before).acts.push({ a, i });
    });

    const box = el("div", { class: "sync" });
    box.append(el("div", { class: "block-head" }, el("h3", {}, "② 문장에 동작 맞추기"),
      el("span", { class: "s-mode " + (info.exact ? "exact" : "guess"),
        title: info.exact ? "목소리 엔진이 실제로 끊어 읽은 문장 경계와 시각입니다" : "문장부호로 추정한 경계입니다. ▶ 듣기를 누르면 실제 시각이 채워집니다" },
        info.exact ? "실제 시각" : "추정"),
      el("span", { class: "hint" }, "줄 = 문장 하나 · 칩 = 그 문장이 시작될 때 실행되는 동작 · 칩을 누르면 카드로 이동")));

    if (total) {
      const bar = el("div", { class: "timebar" });
      sents.forEach((s) => bar.append(el("span", { class: "blk", style: `left:${(s.start / total) * 100}%;width:${((s.end - s.start) / total) * 100}%`, title: `${s.i}번째 문장 ${s.start.toFixed(1)}–${s.end.toFixed(1)}s` }, `${s.i}`)));
      seg.actions.forEach((a, i) => {
        let t = null;
        if (typeof a.at === "number") t = a.at;
        else if (typeof a.at === "string" && /^s\d+$/.test(a.at)) t = sents[Number(a.at.slice(1)) - 1]?.start ?? null;
        if (t === null) return;
        bar.append(el("i", { class: "mark", style: `left:${Math.min(100, (t / total) * 100)}%;background:${actColor(a.do)}`, title: `${actIcon(a.do)} ${actLabel(a.do)} ${summarize(a)} @ ${t.toFixed(1)}s`, onclick: () => onPick(i) }));
      });
      bar.append(el("span", { class: "end" }, `${total.toFixed(1)}s`));
      box.append(bar);
    }

    const table = el("div", { class: "sync-rows" });
    const chip = ({ a, i, warn }) => el("button", { class: "achip" + (warn ? " warn" : ""), style: `--c:${actColor(a.do)}`, title: `${i + 1}. ${actLabel(a.do)} — ${summarize(a)}` + (warn ? "\n이 문장 번호는 대본에 없습니다" : ""), onclick: () => onPick(i) },
      el("b", {}, actIcon(a.do)), el("span", { class: "nm" }, actLabel(a.do)), el("span", { class: "sm" }, short(summarize(a), 26)),
      a.at === undefined || a.at === null || a.at === "" ? null : el("span", { class: "at" }, atText(a.at)));
    const addBtn = (at) => el("button", { class: "addhere", title: "이 문장이 시작될 때 실행되는 동작을 추가", onclick: () => onAddAt(at) }, "＋ 여기서");
    const row = (label, sub, actsList, extraCls = "", at = undefined) => el("div", { class: "srow " + extraCls },
      el("div", { class: "sent" }, el("b", {}, label), sub ? el("span", { class: "t" }, sub) : null),
      el("div", { class: "chips" }, ...(actsList.length ? actsList.map(chip) : [el("span", { class: "none" }, "—")]), at === undefined ? null : addBtn(at)));
    if (before.acts.length) table.append(row("시작", "", before.acts, "pre"));
    rows.forEach(({ s, acts }) => {
      const label = el("span", { class: "sn", title: "문장 번호 — 클릭하면 시작 시점 값(s번호)을 복사", onclick: () => { navigator.clipboard?.writeText("s" + s.i); toast(`s${s.i} 복사됨 — 동작의 ‘시작 시점’ 칸에 붙이세요`); } }, `s${s.i}`);
      const r = el("div", { class: "srow" },
        el("div", { class: "sent" }, label, s.start !== undefined ? el("span", { class: "t" }, `${s.start.toFixed(1)}s`) : null, el("span", { class: "txt", title: s.text }, s.text)),
        el("div", { class: "chips" }, ...(acts.length ? acts.map(chip) : [el("span", { class: "none" }, "—")]), addBtn("s" + s.i)));
      table.append(r);
    });
    numeric.sort((x, y) => x.t - y.t).forEach((r) => table.append(row(`${r.t}s`, "", r.acts, "num")));
    if (!rows.length && !before.acts.length) table.append(el("p", { class: "hint" }, "①에 대본을 쓰면 문장별 줄이 생깁니다."));
    box.append(table);
    return box;
  }

  function field(label, control, hint, key) { return el("div", { class: "field", "data-field": key }, el("label", {}, label), control, hint ? el("span", { class: "hint" }, hint) : null); }
  function inp(value, onchange, attrs = {}) {
    const i = el("input", { type: "text", value: value ?? "", ...attrs });
    i.addEventListener("change", () => onchange(i.value));
    return i;
  }
  function addSegment() {
    state.doc.segments.push({ id: "scene" + (state.doc.segments.length + 1), narration: "", actions: [] });
    state.sel = state.doc.segments.length - 1; touched(); showPane("seg"); renderSegList(); renderSegEditor();
    setTimeout(() => $("#segEditor textarea")?.focus(), 0);
  }
  function moveSeg(d) {
    const i = state.sel, j = i + d;
    if (j < 0 || j >= state.doc.segments.length) return;
    const s = state.doc.segments; [s[i], s[j]] = [s[j], s[i]]; state.sel = j; touched(); renderSegList(); renderSegEditor();
  }
  function dupSeg() {
    const s = JSON.parse(JSON.stringify(state.doc.segments[state.sel])); s.id = (s.id || "scene") + "_copy";
    state.doc.segments.splice(state.sel + 1, 0, s); state.sel += 1; touched(); renderSegList(); renderSegEditor();
  }
  function delSeg() {
    if (!confirm("이 장면을 삭제할까요? (Ctrl+Z 로 되돌릴 수 있습니다)")) return;
    state.doc.segments.splice(state.sel, 1); state.sel = Math.max(0, state.sel - 1); touched(); renderSegList(); renderSegEditor();
  }

  // ------------------------------------------------------------------ 동작 팔레트 (타일로 고르기)
  function openPalette(seg, { at } = {}) {
    const body = el("div", { class: "palette" });
    const search = el("input", { placeholder: "찾기: 판서, 그래프, 강조, write …", autofocus: "" });
    const ctx = at !== undefined ? el("span", { class: "ctx" }, `▶ ${String(at).replace(/^s/, "")}번째 문장에서 시작`) : el("span", { class: "hint" }, "앞 동작이 끝난 뒤 이어서 실행 (나중에 바꿀 수 있어요)");
    body.append(el("h3", {}, "어떤 동작을 넣을까요?"), el("div", { class: "top" }, search, ctx));
    const cats = ["자주 쓰는", ...Object.keys(CAT_COLOR)];
    let curCat = "자주 쓰는";
    const catBar = el("div", { class: "cats" });
    const grid = el("div", { class: "grid" });
    const style = state.doc.meta?.style || "panel";
    const pick = (name) => {
      const t = state.catalogByName[name];
      const act = { do: name, ...(JSON.parse(JSON.stringify(t?.template || {}))) };
      if (at !== undefined) act.at = at; else delete act.at;
      if (name === "goto" && state.doc.layout?.chalk?.sections?.length && !state.doc.layout.chalk.sections.some((s) => s.id === act.section)) act.section = state.doc.layout.chalk.sections[0].id;
      seg.actions.push(act); state.expanded.add(act);
      touched(); closeModal(); renderSegEditor(); renderSegList();
      setTimeout(() => state.focusCard?.(seg.actions.length - 1), 0);
    };
    const tile = (a) => el("button", { class: "tile", style: `--c:${actColor(a.name)}`, title: a.doc_full || a.doc, onclick: () => pick(a.name) },
      el("span", { class: "ico" }, actIcon(a.name)),
      el("span", { class: "nm" }, actLabel(a.name), el("code", { class: "pro-only" }, a.name)),
      el("span", { class: "dc" }, actDoc(a.name)));
    const render = () => {
      catBar.innerHTML = ""; grid.innerHTML = "";
      const q = search.value.trim().toLowerCase();
      for (const c of cats) catBar.append(el("button", { class: c === curCat && !q ? "on" : "", onclick: () => { curCat = c; search.value = ""; render(); } }, c));
      let list;
      if (q) {
        const rank = (a) => (actLabel(a.name).toLowerCase().includes(q) || a.name.includes(q)) ? 0 : 1;   // 이름이 맞는 것을 먼저
        list = state.catalog.filter((a) => `${a.name} ${actLabel(a.name)} ${actDoc(a.name)} ${a.doc} ${a.category}`.toLowerCase().includes(q)).sort((x, y) => rank(x) - rank(y));
      }
      else if (curCat === "자주 쓰는") list = FAVORITES.map((n) => state.catalogByName[n]).filter(Boolean);
      else list = state.catalog.filter((a) => a.category === curCat);
      if (style === "chalkboard") list = list.filter((a) => !a.name.startsWith("board"));
      if (!list.length) grid.append(el("div", { class: "none" }, "일치하는 동작이 없습니다"));
      for (const a of list) grid.append(tile(a));
    };
    search.addEventListener("input", render);
    body.append(catBar, grid, el("p", { class: "hint", style: "margin:10px 0 0" }, "칠판 판서·식 전개는 칠판(chalkboard) 스타일, 보드 계열은 패널(panel) 스타일에서 씁니다. 지금 스타일: ", el("b", {}, style)));
    render();
    modal(body, true);
    setTimeout(() => search.focus(), 0);
  }

  // ------------------------------------------------------------------ 동작 카드
  function actionCard(seg, act, i) {
    const spec = state.catalogByName[act.do];
    const color = actColor(act.do);
    const open = state.expanded.has(act);
    const card = el("div", { class: "card" + (open ? " open" : ""), style: `--c:${color}` });
    const nSent = sentencesFor(seg).list.length;
    const atWarn = typeof act.at === "string" && /^s\d+$/.test(act.at) && Number(act.at.slice(1)) > Math.max(1, nSent);
    if (atWarn) card.classList.add("at-warn");

    // 카드를 바꾸는 동안 포커스된 입력이 blur → 브라우저가 change 를 한 번 더 쏘며 재진입할 수 있어 막는다
    const rerenderCard = () => { if (!card.isConnected || card._replacing) return; card._replacing = true; const n = actionCard(seg, act, i); card.replaceWith(n); state.renderStage?.(); };
    const timingText = act.at === undefined || act.at === null || act.at === "" ? "이어서" : typeof act.at === "number" ? `▶ ${act.at}s` : `▶ ${String(act.at).replace(/^s(\d+)$/, "$1번째 문장")}`;
    const head = el("div", { class: "head", onclick: (e) => { if (e.target.closest("button, input, select")) return; if (open) state.expanded.delete(act); else { state.expanded.add(act); state.cursor = { seg: state.sel, act: i }; } rerenderCard(); } },
      el("span", { class: "idx" }, String(i + 1)),
      el("span", { class: "ico" }, actIcon(act.do)),
      el("span", { class: "name" }, actLabel(act.do), el("code", { class: "pro-only" }, act.do)),
      el("span", { class: "sum", title: summarize(act) }, summarize(act) ? summaryNode(act) : el("i", { class: "hint" }, spec ? actDoc(act.do) : "알 수 없는 동작")),
      el("span", { class: "timing" + (atWarn ? " warn" : "") + (act.at === undefined ? " seq" : ""), title: atWarn ? `대본에 문장이 ${nSent}개뿐입니다` : "시작 시점" }, timingText),
      act.run_time !== undefined ? el("span", { class: "rt", title: "길이(초)" }, `${act.run_time}s`) : null,
      el("span", { class: "tools" },
        el("button", { class: "ghost mini", title: "위로", onclick: () => swapAct(seg, i, -1) }, "↑"),
        el("button", { class: "ghost mini", title: "아래로", onclick: () => swapAct(seg, i, 1) }, "↓"),
        el("button", { class: "ghost mini", title: "복제", onclick: () => { seg.actions.splice(i + 1, 0, JSON.parse(JSON.stringify(act))); touched(); renderSegEditor(); renderSegList(); } }, "⧉"),
        el("button", { class: "ghost mini", title: "삭제", onclick: () => { seg.actions.splice(i, 1); touched(); renderSegEditor(); renderSegList(); toast(`${actLabel(act.do)} 동작을 지웠습니다 (Ctrl+Z 로 되돌리기)`); } }, "✕")),
      el("span", { class: "chev" }, open ? "▾" : "▸"));
    card.append(head);
    if (!open) return card;

    const body = el("div", { class: "body" });
    body.append(actionPreview(seg, act, i));

    // 종류 / 시작 시점 / 길이
    const doSel = el("select", { class: "do", title: "동작 종류 바꾸기" });
    let lastCat = null;
    for (const a of state.catalog) {
      if (a.category !== lastCat) { lastCat = a.category; doSel.append(el("optgroup", { label: a.category })); }
      doSel.lastChild.append(el("option", { value: a.name }, `${actIcon(a.name)} ${actLabel(a.name)}${state.pro ? ` (${a.name})` : ""}`));
    }
    if (!spec) doSel.append(el("option", { value: act.do }, act.do + " (?)"));
    doSel.value = act.do;
    doSel.addEventListener("change", () => { act.do = doSel.value; touched(); renderSegEditor(); });
    const sents = sentencesFor(seg).list;
    const atPick = el("select", { class: "atpick", title: "언제 시작할지: 문장을 고르면 그 문장을 읽기 시작할 때 실행됩니다" });
    atPick.append(el("option", { value: "__seq" }, "이어서 (앞 동작이 끝난 뒤)"));
    sents.forEach((s) => atPick.append(el("option", { value: "s" + s.i }, `${s.i}번째 문장${s.start !== undefined ? ` (${s.start.toFixed(1)}s)` : ""} — ${short(s.text, 34)}`)));
    atPick.append(el("option", { value: "__num" }, "장면 시작 뒤 n초…"));
    if (typeof act.at === "string" && /^s\d+$/.test(act.at)) { if (![...atPick.options].some((o) => o.value === act.at)) atPick.append(el("option", { value: act.at }, `${act.at.slice(1)}번째 문장 (없음!)`)); atPick.value = act.at; }
    else if (typeof act.at === "number") atPick.value = "__num";
    else atPick.value = "__seq";
    const atNum = el("input", { class: "at", type: "number", step: "0.1", min: "0", value: typeof act.at === "number" ? act.at : "", placeholder: "초", title: "장면 시작 뒤 몇 초에 실행" });
    atNum.classList.toggle("hidden", typeof act.at !== "number");
    atNum.addEventListener("change", () => { const v = parseVal(atNum.value); if (v === undefined) delete act.at; else act.at = Number(v); touched(); renderSegEditor(); });
    atPick.addEventListener("change", () => {
      if (atPick.value === "__seq") { delete act.at; touched(); renderSegEditor(); }
      else if (atPick.value === "__num") { atNum.classList.remove("hidden"); atNum.focus(); if (typeof act.at !== "number") { act.at = 0; touched(); } }
      else { act.at = atPick.value; touched(); renderSegEditor(); }
    });
    const rtIn = el("input", { class: "rt", type: "number", step: "0.1", min: "0", value: act.run_time ?? "", placeholder: "자동", title: "애니메이션 길이(초). 비우면 동작별 기본값" });
    rtIn.addEventListener("change", () => { const v = parseVal(rtIn.value); if (v === undefined) delete act.run_time; else act.run_time = v; touched(); rerenderCard(); });
    body.append(el("div", { class: "ctl" },
      el("span", { class: "ctl-item" }, el("label", {}, "종류"), doSel),
      el("span", { class: "ctl-item" }, el("label", {}, "시작 시점"), atPick, atNum),
      el("span", { class: "ctl-item" }, el("label", {}, "길이"), rtIn, el("label", {}, "초"))));
    if (spec) body.append(el("p", { class: "doc" }, state.pro && spec.doc_full ? spec.doc_full : actDoc(act.do)));

    // 파라미터
    const params = el("div", { class: "params" });
    const skip = new Set(["do", "at", "run_time", "steps", "parts"]);
    const stepKeys = ["why", "from", "focus", "new", "cancel", "box", "pulse", "hold", "cancel_at", "underline", "same_line", "space"];
    const known = (spec?.params || []).map((p) => p.name).filter((n) => !skip.has(n));
    const setKeys = Object.keys(act).filter((k) => !skip.has(k) && !(act.do === "step" && stepKeys.includes(k)));
    const unset = known.filter((k) => !(k in act) && !(act.do === "step" && stepKeys.includes(k)));
    const required = (spec?.params || []).filter((p) => p.required && !skip.has(p.name)).map((p) => p.name);
    for (const k of [...required.filter((k) => !setKeys.includes(k)), ...setKeys]) {
      const pspec = (spec?.params || []).find((p) => p.name === k);
      const editor = paramEditor(act, k, pspec, () => { touched(); rerenderCard(); });
      params.append(
        el("span", { class: "k" + (pspec?.required ? " req" : "") + (pspec ? "" : " extra"), title: (paramHint(k) ? paramHint(k) + "\n" : "") + (pspec ? `${k}: ${pspec.type || ""}${pspec.required ? " · 필수" : ""}` : `${k}: 카탈로그에 없는 항목 (hooks 인자 등)`) },
          paramLabel(act.do, k), el("small", {}, k)),
        editor,
        el("span", { class: "x", title: "이 항목 지우기 (기본값으로)", onclick: () => { delete act[k]; touched(); rerenderCard(); } }, "✕"));
    }
    body.append(params);
    ensureDatalists();

    const addP = el("select", { class: "addp" });
    addP.append(el("option", { value: "" }, unset.length ? `＋ 설정 항목 추가 (${unset.length}개 더)…` : "＋ 설정 항목 추가…"));
    for (const k of unset) { const p = (spec?.params || []).find((q) => q.name === k); addP.append(el("option", { value: k }, `${paramLabel(act.do, k)}${state.pro ? ` (${k})` : ""}${p && p.default !== null && p.default !== undefined ? ` — 기본 ${fmtVal(p.default)}` : ""}`)); }
    if (state.pro || act.do === "custom") addP.append(el("option", { value: "__custom" }, "직접 입력…"));
    addP.addEventListener("change", () => {
      let k = addP.value; if (!k) return;
      if (k === "__custom") { k = prompt("추가할 항목 이름 (YAML 키)"); if (!k) return; }
      const p = (spec?.params || []).find((q) => q.name === k);
      act[k] = p && p.default !== null && p.default !== undefined ? JSON.parse(JSON.stringify(p.default)) : (p && /^bool/.test(p.type) ? true : p && /^list/.test(p.type) ? [] : "");
      touched(); rerenderCard();
    });
    const rawBtn = el("button", { class: "ghost mini pro-only", onclick: () => { state.rawOpen.has(act) ? state.rawOpen.delete(act) : state.rawOpen.add(act); rerenderCard(); } }, state.rawOpen.has(act) ? "JSON 닫기" : "JSON 으로 보기");
    body.append(el("div", { class: "foot" }, addP, el("span", { class: "hint" }, act.do === "custom" ? "함수 인자는 ‘직접 입력…’ 으로 이름을 추가하세요" : ""), el("span", { class: "spacer" }), rawBtn));

    if (act.do === "derive") body.append(stepsEditor(act.steps = act.steps || [], () => { touched(); state.renderStage?.(); }, false, sents));
    if (act.do === "step") body.append(stepsEditor([act], () => { touched(); state.renderStage?.(); }, true, sents));

    if (state.rawOpen.has(act)) {
      const ta = el("textarea", { class: "raw", spellcheck: "false" });
      ta.value = JSON.stringify(act, null, 2);
      ta.addEventListener("change", () => {
        try { const o = JSON.parse(ta.value); for (const k of Object.keys(act)) delete act[k]; Object.assign(act, o); touched(); rerenderCard(); }
        catch (e) { toast("JSON 오류: " + e.message, "bad"); }
      });
      body.append(ta);
    }
    card.append(body);
    return card;
  }

  const COLOR_NAMES = ["chalk", "accent", "highlight", "exp", "log", "q1", "q2", "point", "rect", "axis_sym", "guide", "ok", "warn", "muted", "text"];
  const COLOR_HEX = { chalk: "#f2f2e6", accent: "#ffd23f", highlight: "#ff9f43", exp: "#7cc4ff", log: "#ff7ab6", q1: "#5ad48a", q2: "#b48cff", point: "#ffd23f", rect: "#4fd1c5", axis_sym: "#bbb", guide: "#888", ok: "#5ad48a", warn: "#ff9f43", muted: "#8b93a7", text: "#e6e9f0" };
  const COLOR_KO = { chalk: "분필(흰)", accent: "노랑", highlight: "주황", exp: "하늘", log: "핑크", q1: "초록", q2: "보라", point: "점(노랑)", rect: "청록", axis_sym: "회색(축)", guide: "회색(보조)", ok: "초록", warn: "주황", muted: "흐린", text: "글자" };

  /** 파라미터 하나의 입력기. 종류(kind)에 따라 목록/숫자/체크/선택/색/좌표/JSON. */
  function paramEditor(act, k, pspec, onchange) {
    const wrap = el("div", { class: "v" });
    const val = act[k];
    const kind = paramKind(act, k, pspec);
    const set = (v) => { if (v === undefined || v === "" || (Array.isArray(v) && !v.length)) delete act[k]; else act[k] = v; onchange(); };
    const ph = pspec && pspec.default !== null && pspec.default !== undefined ? `기본 ${fmtVal(pspec.default)}` : (pspec?.required ? "필수" : "");
    const isMath = MATH_KEYS.has(k) && !(PLAIN_TEXT_ACTS.has(act.do) && (k === "title" || k === "text" || k === "subtitle")) && !(act.do === "problem" && k === "title");
    const onlyMath = k === "tex" || k === "label" || k === "x_label" || k === "y_label" || k === "arrow_label";
    switch (kind) {
      case "bool": {
        const c = el("input", { type: "checkbox" }); c.checked = val === undefined ? !!(pspec?.default) : !!val;
        c.addEventListener("change", () => { act[k] = c.checked; onchange(); });
        wrap.append(el("label", { class: "chk" }, c, c.checked ? "켬" : "끔", pspec?.default !== undefined && pspec?.default !== null ? el("span", { class: "hint" }, ` (기본 ${pspec.default ? "켬" : "끔"})`) : null));
        return wrap;
      }
      case "num": {
        const i = el("input", { type: "number", step: "any", value: val ?? "", placeholder: ph, class: "mono" });
        i.addEventListener("change", () => set(i.value === "" ? undefined : Number(i.value)));
        wrap.append(i); if (paramHint(k)) wrap.append(el("div", { class: "sub" }, paramHint(k)));
        return wrap;
      }
      case "select": {
        const s = el("select", {});
        s.append(el("option", { value: "" }, ph || "선택…"));
        for (const [v, lab] of SELECT_OPTIONS[k]) s.append(el("option", { value: v }, lab + (state.pro && lab !== v ? ` (${v})` : "")));
        s.value = val ?? ""; s.addEventListener("change", () => set(s.value || undefined));
        wrap.append(s); return wrap;
      }
      case "section": {
        const secs = state.doc.layout?.chalk?.sections || [];
        const s = el("select", {});
        s.append(el("option", { value: "" }, "칸 선택…"));
        for (const sc of secs) s.append(el("option", { value: sc.id }, `${sc.title || sc.id}${sc.title ? ` (${sc.id})` : ""} · ${sc.layout === "split" ? "그림+판서" : "판서"}`));
        if (val && !secs.some((x) => x.id === val)) s.append(el("option", { value: val }, `${val} (설정에 없는 칸!)`));
        s.value = val ?? ""; s.addEventListener("change", () => set(s.value || undefined));
        wrap.append(s, el("div", { class: "sub" }, secs.length ? "칸은 ⚙ 영상 설정에서 추가/이름 변경" : "⚙ 영상 설정 → 칠판 칸에서 칸을 먼저 만드세요"));
        return wrap;
      }
      case "color": {
        const row = el("div", { class: "colorsel" });
        for (const c of COLOR_NAMES) row.append(el("button", { type: "button", class: val === c ? "on" : "", title: c, onclick: () => set(val === c ? undefined : c) }, el("i", { class: "swatch", style: `background:${COLOR_HEX[c]}` }), COLOR_KO[c] || c));
        if (val && !COLOR_NAMES.includes(val)) row.append(el("button", { type: "button", class: "on" }, val));
        wrap.append(row); return wrap;
      }
      case "fn": {
        const i = el("input", { value: val ?? "", placeholder: "hooks.py 의 함수 이름", class: "mono", list: "hooksList" });
        i.addEventListener("change", () => set(i.value.trim() || undefined));
        wrap.append(i, el("div", { class: "sub" }, state.hooks.length ? `이 프로젝트의 함수: ${state.hooks.join(", ")}` : "이 프로젝트 폴더에 hooks.py 가 없습니다"));
        return wrap;
      }
      case "lines": {
        const list = Array.isArray(val) ? val : val === undefined ? [] : [String(val)];
        const ta = el("textarea", { rows: Math.max(2, Math.min(8, list.length + 1)), spellcheck: "false", placeholder: "한 줄에 하나씩" });
        ta.value = list.join("\n");
        ta.addEventListener("change", () => set(ta.value.split("\n").map((x) => x.replace(/\s+$/, "")).filter((x) => x.trim().length)));
        wrap.append(ta);
        if (isMath) {
          let prev = mathPreview(list);
          wrap.append(prev);
          ta.addEventListener("input", () => { const n = mathPreview(ta.value.split("\n").filter((x) => x.trim().length)); prev.replaceWith(n); prev = n; });
          wrap.append(symbolBar(ta, () => ta.dispatchEvent(new Event("input"))));
        }
        wrap.append(el("div", { class: "sub" }, paramHint(k) || "한 줄에 하나씩"));
        return wrap;
      }
      case "csv": {
        const list = Array.isArray(val) ? val : val === undefined ? [] : [val];
        const i = el("input", { value: list.join(", "), placeholder: ph || "이름1, 이름2", class: "mono" });
        i.addEventListener("change", () => { const arr = i.value.split(/\s*,\s*/).filter((x) => x.length); set(arr.length ? (arr.length === 1 && typeof val === "string" ? arr[0] : arr) : undefined); });
        wrap.append(i, el("div", { class: "sub" }, paramHint(k) || "쉼표로 여러 개"));
        return wrap;
      }
      case "nums": {
        const i = el("input", { value: Array.isArray(val) ? val.join(", ") : val ?? "", placeholder: ph || (k === "pos" ? "예: 1, 2" : "예: -3, 3"), class: "mono" });
        i.addEventListener("change", () => set(parseList(i.value)));
        wrap.append(i, el("div", { class: "sub" }, paramHint(k) || "쉼표로 구분한 숫자"));
        return wrap;
      }
      case "json": {
        const ta = el("textarea", { rows: 3, spellcheck: "false", class: "mono json", placeholder: paramHint(k) || "JSON" });
        ta.value = val === undefined ? "" : JSON.stringify(val);
        ta.addEventListener("change", () => { const t = ta.value.trim(); if (!t) return set(undefined); try { set(JSON.parse(t)); } catch (e) { toast("JSON 형식이 아닙니다: " + e.message, "bad"); } });
        wrap.append(ta, el("div", { class: "sub" }, paramHint(k) || "JSON 형식"));
        return wrap;
      }
      default: {
        const long = typeof val === "string" && val.length > 60;
        const i = long ? el("textarea", { rows: Math.min(6, 1 + Math.ceil(val.length / 70)), spellcheck: "false" }) : el("input", { spellcheck: "false" });
        i.value = val === undefined ? "" : fmtVal(val); i.placeholder = ph;
        if (k === "id" || k === "of" || k === "expr" || k === "source" || k === "point" || k === "near" || k === "focus") i.classList.add("mono");
        i.addEventListener("change", () => { const v = (k === "id" || k === "of" || k === "expr" || k === "source" || k === "point" || k === "near") ? (i.value.trim() || undefined) : parseVal(i.value); set(v); });
        wrap.append(i);
        if (isMath) {
          let prev = mathPreview(val ?? "", { onlyMath, ko: !!act.ko });
          wrap.append(prev);
          i.addEventListener("input", () => { const n = mathPreview(i.value, { onlyMath, ko: !!act.ko }); prev.replaceWith(n); prev = n; });
          wrap.append(symbolBar(i, () => i.dispatchEvent(new Event("input"))));
        }
        if (paramHint(k)) wrap.append(el("div", { class: "sub" }, paramHint(k)));
        return wrap;
      }
    }
  }

  function swapAct(seg, i, d) {
    const j = i + d; if (j < 0 || j >= seg.actions.length) return;
    [seg.actions[i], seg.actions[j]] = [seg.actions[j], seg.actions[i]]; touched(); renderSegEditor();
  }
  function ensureDatalists() {
    const fill = (id, values) => {
      let dl = $("#" + id);
      if (!dl) { dl = el("datalist", { id }); document.body.append(dl); }
      dl.innerHTML = ""; for (const v of values) dl.append(el("option", { value: v }));
    };
    fill("hooksList", state.hooks);
    fill("sectionsList", (state.doc.layout?.chalk?.sections || []).map((s) => s.id));
    fill("colorsList", COLOR_NAMES);
  }

  /** derive.steps 또는 step 액션 하나를 편집하는 표. */
  function stepsEditor(steps, onchange, single = false, sents = []) {
    const box = el("div", { class: "steps" });
    const optOpen = new Set();
    const isOp = (p) => p === "=" || /^[+\-−×·,]$/.test(p) || /^\\(times|cdot|pm|Rightarrow|le|ge|ne)$/.test(p);
    const render = () => {
      box.innerHTML = "";
      box.append(el("div", { class: "block-head" }, el("h4", {}, single ? "이 단계의 식" : `전개 단계 ${steps.length}개`),
        el("span", { class: "spacer" }),
        single ? null : el("button", { class: "mini", onclick: () => { steps.push({ parts: ["=", ""] }); onchange(); render(); } }, "＋ 단계")));
      box.append(el("p", { class: "example" }, "식을 ", el("code", {}, "|"), " 로 조각내어 쓰세요. 앞 단계와 같은 조각은 그대로 미끄러지고, 바뀐 조각만 강조되며 날아옵니다. 예: ", el("code", {}, "x^{2} | + | 2x | = | 0"), " → ", el("code", {}, "x(x+2) | = | 0")));
      steps.forEach((st, k) => {
        const parts = st.parts || (st.tex ? [st.tex] : []);
        const preview = el("div", { class: "preview" });
        parts.forEach((p) => { const pc = el("span", { class: "pc" + (isOp(p) ? " op" : "") }); if (hasKatex() && p.trim()) katexInto(pc, p); else pc.textContent = stripTex(p) || " "; preview.append(pc); });
        if (st.why) preview.append(el("span", { class: "why" }, "(∵ ", mathLine(st.why), ")"));
        const flags = [st.box ? "상자" : "", st.pulse ? "펄스" : "", st.cancel ? "소거" : "", st.from ? "대입" : "", st.at ? `▶ ${atText(st.at)}` : "", st.hold ? `hold ${st.hold}` : ""].filter(Boolean);
        flags.forEach((f) => preview.append(el("span", { class: "flag" }, f)));

        const partsIn = el("input", { value: joinParts(parts), placeholder: "조각 | 조각 | …  (예: = | 2^{3} | \\times | x)", spellcheck: "false", title: "LaTeX 조각들을 | 로 구분" });
        partsIn.addEventListener("change", () => { st.parts = splitParts(partsIn.value); delete st.tex; onchange(); render(); });
        const whyIn = el("input", { value: st.why || "", placeholder: "이유 (예: 양변에 $t$ 를 곱한다)", spellcheck: "false", title: "이 단계로 넘어가는 이유. 오른쪽에 (∵ …) 로 적힙니다" });
        whyIn.addEventListener("change", () => { if (whyIn.value.trim()) st.why = whyIn.value; else delete st.why; onchange(); render(); });
        const optBtn = el("button", { class: "ghost mini", onclick: () => { optOpen.has(st) ? optOpen.delete(st) : optOpen.add(st); render(); } }, optOpen.has(st) ? "세부 ▾" : "세부 ▸");
        const row = el("div", { class: "step" },
          el("span", { class: "n" }, single ? "" : String(k + 1)),
          el("div", { class: "main" }, preview,
            el("div", { class: "inputs" }, partsIn, whyIn)),
          el("span", { class: "tools" }, optBtn,
            single ? null : el("button", { class: "ghost mini", title: "위로", onclick: () => { if (k > 0) { [steps[k - 1], steps[k]] = [steps[k], steps[k - 1]]; onchange(); render(); } } }, "↑"),
            single ? null : el("button", { class: "ghost mini", title: "삭제", onclick: () => { steps.splice(k, 1); onchange(); render(); } }, "✕")));
        if (optOpen.has(st)) {
          const opts = el("div", { class: "opts" });
          const chk = (key, label, tip) => { const c = el("input", { type: "checkbox", title: tip }); c.checked = !!st[key]; c.addEventListener("change", () => { if (c.checked) st[key] = true; else delete st[key]; onchange(); render(); }); return el("label", { title: tip }, c, label); };
          const txt = (key, label, cls = "small", ph = "", tip = "") => { const t = el("input", { class: cls, value: st[key] === undefined ? "" : fmtVal(st[key]), placeholder: ph, title: tip, spellcheck: "false" }); t.addEventListener("change", () => { const v = parseVal(t.value); if (v === undefined) delete st[key]; else st[key] = v; onchange(); render(); }); return el("label", { title: tip }, label, t); };
          const atSel = el("select", { class: "small" }); atSel.append(el("option", { value: "" }, "문장…")); sents.forEach((s) => atSel.append(el("option", { value: "s" + s.i }, `${s.i}번째`)));
          atSel.addEventListener("change", () => { if (atSel.value) { st.at = atSel.value; onchange(); render(); } });
          opts.append(
            el("div", { class: "grp" }, el("b", {}, "시각"), txt("at", "시작", "small", "s2", "이 단계를 시작할 문장(s번호) 또는 초"), atSel, txt("hold", "hold", "small", "s3", "출처 상자만 먼저 짚어 두고 이 문장부터 움직임"), txt("run_time", "길이", "small", "2.0", "단계 애니메이션 길이(초)")),
            el("div", { class: "grp" }, el("b", {}, "강조"), chk("box", "상자", "결과에 분필 상자"), chk("pulse", "펄스", "상자를 한 번 두드림"), chk("underline", "밑줄", "")),
            el("div", { class: "grp" }, el("b", {}, "매칭"), txt("from", "대입", "wide", '{"2^{2}": "x^{2}"}', "대입: 새 조각 ← 이전 조각 (JSON)"), txt("focus", "출처", "wide", '["2\\\\cdot3x^{2}"]', "출처를 이 조각들로 한정 (JSON)"), txt("new", "새 조각", "wide", '["6", "x^{2}"]', "완전히 새로 쓰는 조각 (JSON)")),
            el("div", { class: "grp" }, el("b", {}, "소거"), txt("cancel", "취소선", "wide", '["a_7", 5]', "취소선을 그을 조각(문자열/인덱스, JSON)"), txt("cancel_at", "시점", "small", "s5", "취소선을 긋는 문장")),
          );
          row.append(opts);
        }
        box.append(row);
      });
    };
    render();
    return box;
  }

  // ------------------------------------------------------------------ 영상 설정
  function renderSettings() {
    const pane = $("#settingsEditor");
    pane.innerHTML = "";
    const doc = state.doc;
    doc.meta = doc.meta || {}; doc.layout = doc.layout || {}; doc.layout.chalk = doc.layout.chalk || {}; doc.params = doc.params || {};
    const m = doc.meta, ch = doc.layout.chalk;
    const set = (obj, key, cast = (v) => v) => (v) => { const x = cast(v); if (x === undefined || x === "") delete obj[key]; else obj[key] = x; touched(); if (obj === m && key === "title") loadProjects(); };
    const num = (v) => (v === "" ? undefined : Number(v));
    const sel = (value, options, onchange) => { const s = el("select", {}); for (const o of options) { const [v, lab] = Array.isArray(o) ? o : [o, o]; s.append(el("option", { value: v }, lab)); } s.value = value; s.addEventListener("change", () => onchange(s.value)); return s; };

    const wrap = el("div", { class: "settings" });
    wrap.append(el("h2", {}, "영상 정보"));
    const g = el("div", { class: "grid2" });
    g.append(field("제목", inp(m.title, set(m, "title")), null, "meta.title"), field("부제", inp(m.subtitle, set(m, "subtitle")), null, "meta.subtitle"),
      field("프로젝트 ID", inp(m.id, set(m, "id"), { class: "mono" }), `결과 영상 폴더 이름. 보통 프로젝트 폴더 이름(${state.pid})과 같게 둡니다`, "meta.id"),
      field("목소리", sel(m.voice || "ko-KR-InJoonNeural", [["ko-KR-InJoonNeural", "인준 (남성)"], ["ko-KR-SunHiNeural", "선히 (여성)"], ["ko-KR-HyunsuMultilingualNeural", "현수 (남성, 다국어)"]], set(m, "voice")), null, "meta.voice"),
      field("말 속도", sel(m.rate || "+0%", [["-20%", "느리게 (-20%)"], ["-10%", "조금 느리게 (-10%)"], ["+0%", "보통"], ["+10%", "조금 빠르게 (+10%)"], ["+20%", "빠르게 (+20%)"]], set(m, "rate")), null, "meta.rate"),
      field("해상도", sel(m.resolution || "1080p", ["480p", "720p", "1080p", "1440p", "2160p"], set(m, "resolution")), "최종 렌더에만 적용. 미리보기는 항상 480p", "meta.resolution"),
      field("fps", inp(m.fps ?? 30, set(m, "fps", num)), null, "meta.fps"),
      field("스타일", sel(m.style || "panel", [["chalkboard", "칠판 (손글씨 판서)"], ["panel", "패널 (보드)"]], set(m, "style")), null, "meta.style"),
      field("자막", sel(m.subtitles || "burn", [["burn", "영상에 새김"], ["soft", "별도 파일(srt)"], ["none", "없음"]], set(m, "subtitles")), null, "meta.subtitles"),
      field("장면 사이 쉼", inp(m.segment_pad ?? 0.45, set(m, "segment_pad", num)), "초", "meta.segment_pad"));
    wrap.append(g);

    wrap.append(el("h2", {}, "칠판 배치 (칠판 스타일일 때)"));
    const g2 = el("div", { class: "grid2" });
    g2.append(field("글자 크기", inp(ch.line_scale ?? 0.72, set(ch, "line_scale", num), { title: "판서 수식 배율" })),
      field("줄 간격", inp(ch.line_gap ?? 0.26, set(ch, "line_gap", num))),
      field("그림 영역 폭", inp(ch.graph_width ?? 7.2, set(ch, "graph_width", num))),
      field("하단 여백", inp(ch.bottom_reserve ?? 1.1, set(ch, "bottom_reserve", num), { title: "자막 띠를 피해 비워 두는 높이" })));
    wrap.append(g2);

    const secs = el("div", { class: "sections" });
    const renderSecs = () => {
      secs.innerHTML = "";
      ch.sections = ch.sections || [];
      secs.append(el("div", { class: "row" }, el("span", { class: "hint" }, "칠판 칸: 칠판은 왼쪽→오른쪽으로 이어진 칸들이고, ‘칠판 칸 이동’ 동작으로 카메라가 옮겨 갑니다. ‘그림+판서’ 칸은 왼쪽에 그래프, 오른옽에 판서."),
        el("span", { class: "spacer" }), el("button", { class: "mini", onclick: () => { ch.sections.push({ id: "sec" + (ch.sections.length + 1), title: "", layout: "full" }); touched(); renderSecs(); } }, "＋ 칸")));
      if (ch.sections.length) secs.append(el("div", { class: "sec hint" }, el("span", {}, "이름(id)"), el("span", {}, "판서 제목"), el("span", {}, "배치"), el("span", {}, "그림 폭"), el("span", {})));
      ch.sections.forEach((s, i) => {
        secs.append(el("div", { class: "sec" },
          inp(s.id, (v) => { s.id = v; touched(); }, { placeholder: "id (영문)" }),
          inp(s.title || "", (v) => { s.title = v; touched(); }, { placeholder: "칸 위에 적히는 제목" }),
          sel(s.layout || "full", [["full", "판서 전체"], ["split", "그림+판서"]], (v) => { s.layout = v; touched(); }),
          inp(s.graph_width ?? "", (v) => { const n = num(v); if (n === undefined) delete s.graph_width; else s.graph_width = n; touched(); }, { placeholder: "기본" }),
          el("span", {}, el("button", { class: "ghost mini", onclick: () => { if (i > 0) { [ch.sections[i - 1], ch.sections[i]] = [ch.sections[i], ch.sections[i - 1]]; touched(); renderSecs(); } } }, "↑"),
            el("button", { class: "ghost mini", onclick: () => { ch.sections.splice(i, 1); touched(); renderSecs(); } }, "✕"))));
      });
      const map = boardMap(null, null); if (map) secs.append(map);
    };
    renderSecs();
    wrap.append(secs);

    wrap.append(el("h2", {}, "상수 (params)"), el("p", { class: "desc" }, "수식·그래프 식에서 이름으로 쓰는 값. 예: k_b = 0.5 로 두고 expr 에 k_b 를 쓰면 한 곳만 고쳐도 전체가 바뀝니다."));
    const kv = el("div", {});
    const renderKv = () => {
      kv.innerHTML = "";
      for (const [k, v] of Object.entries(doc.params)) {
        kv.append(el("div", { class: "kv" }, el("code", {}, k), inp(fmtVal(v), (x) => { doc.params[k] = parseVal(x); touched(); }),
          el("button", { class: "ghost mini", onclick: () => { delete doc.params[k]; touched(); renderKv(); } }, "✕")));
      }
      const nk = el("input", { placeholder: "새 상수 이름 (Enter)" });
      nk.addEventListener("keydown", (e) => { if (e.key === "Enter" && nk.value.trim()) { doc.params[nk.value.trim()] = 0; touched(); renderKv(); } });
      kv.append(nk);
    };
    renderKv();
    wrap.append(kv);
    pane.append(wrap);
  }

  // ------------------------------------------------------------------ 패널 전환
  function showPane(which) {
    $("#segEditor").classList.toggle("hidden", which !== "seg");
    $("#settingsEditor").classList.toggle("hidden", which !== "settings");
    $("#yamlEditor").classList.toggle("hidden", which !== "yaml");
    if (which === "settings") renderSettings();
    if (which === "yaml") refreshYaml();
  }
  async function refreshYaml() {
    if (state.yamlDirty || !state.dirty) { $("#yamlText").value = state.yamlText; return; }
    try { const r = await api("/api/yaml/format", { method: "POST", body: { doc: state.doc } }); state.yamlText = r.yaml; $("#yamlText").value = r.yaml; }
    catch (e) { toast(e.message, "bad"); }
  }

  // ------------------------------------------------------------------ 저장/검사
  async function save() {
    if (!state.pid) return;
    try {
      const body = state.yamlDirty ? { yaml: $("#yamlText").value } : { doc: state.doc };
      const r = await api(`/api/projects/${state.pid}`, { method: "PUT", body });
      state.yamlText = r.yaml; state.doc = r.doc; state.yamlDirty = false; state.snap = JSON.stringify(state.doc); setDirty(false);
      if (r.sentences) setSentences(r.sentences, r.doc);
      showCheck(r.check);
      toast(r.check.ok ? "저장했습니다 ✓" : `저장했습니다 — 고칠 곳 ${r.check.errors.length}개 (오른쪽 ‘문제점’ 탭)`, r.check.ok ? "ok" : "bad");
      if (!r.check.ok) switchTab("check");
      renderSegList(); renderSegEditor();
      $("#yamlText").value = state.yamlText;
      loadProjects();
      return true;
    } catch (e) { toast("저장 실패: " + e.message, "bad"); return false; }
  }

  async function validate(tex) {
    if (!state.pid) return;
    const btn = tex ? $("#btnTex") : $("#btnValidate");
    btn.disabled = true; const old = btn.textContent; if (tex) btn.textContent = "수식 컴파일 중…";
    try {
      const body = state.yamlDirty ? { yaml: $("#yamlText").value, tex } : { doc: state.doc, tex };
      const r = await api(`/api/projects/${state.pid}/validate`, { method: "POST", body });
      showCheck(r); switchTab("check");
      toast(r.ok ? (tex ? "수식까지 모두 통과 ✓" : "구조 검사 통과 ✓") : `고칠 곳 ${r.errors.length}개`, r.ok ? "ok" : "bad");
    } catch (e) { toast(e.message, "bad"); }
    btn.disabled = false; btn.textContent = old;
  }

  function showCheckBadge(r) {
    const b = $("#checkBadge");
    if (!r || (!r.errors?.length && !r.warnings?.length)) { b.classList.add("hidden"); return; }
    b.classList.remove("hidden"); b.className = "badge" + (r.errors.length ? "" : " warn"); b.textContent = String(r.errors.length || r.warnings.length);
  }
  /** 문제 항목의 target({seg, act} | {pane, field}) 으로 이동. */
  function jumpTo(target) {
    if (!target) return false;
    if (target.pane === "settings") {
      showPane("settings");
      const f = target.field && $(`#settingsEditor [data-field="${target.field}"]`);
      if (f) { f.scrollIntoView({ behavior: "smooth", block: "center" }); f.classList.add("flash"); setTimeout(() => f.classList.remove("flash"), 1600); f.querySelector("input, select")?.focus(); }
      return true;
    }
    if (target.pane === "yaml") { if (!state.pro) setPro(true); showPane("yaml"); return true; }
    if (target.seg === undefined) return false;
    selectSegment(target.seg);
    if (target.act !== undefined) setTimeout(() => state.focusCard?.(target.act), 50);
    return true;
  }
  function showCheck(r) {
    state.lastCheck = r; showCheckBadge(r);
    const box = $("#checkBox");
    box.innerHTML = "";
    const nE = (r.errors || []).length, nW = (r.warnings || []).length;
    box.append(el("div", { class: "check-sum " + (nE ? "bad" : nW ? "warn" : "ok") },
      el("b", {}, nE ? `고칠 곳 ${nE}개` : nW ? "렌더는 할 수 있어요" : "문제 없음 ✓"),
      el("span", {}, nE ? "아래를 고쳐야 영상을 만들 수 있습니다." + (nW ? ` 확인해 볼 곳도 ${nW}개 있어요.` : "")
        : nW ? `확인해 볼 곳이 ${nW}개 있습니다.` : "이제 상단의 미리보기 버튼을 눌러 보세요."),
      r.summary?.segments !== undefined ? el("small", {}, `장면 ${r.summary.segments}개 · 동작 ${r.summary.actions}개 검사`) : null));
    const issue = (kind, e) => el("div", { class: "issue " + kind },
      el("div", { class: "top" },
        el("span", { class: "tag" }, kind === "err" ? "고쳐야 함" : "확인"),
        el("span", { class: "loc" }, e.label || e.where),
        el("span", { class: "spacer" }),
        e.target ? el("button", { class: "mini" + (kind === "err" ? " accent" : ""), onclick: () => jumpTo(e.target) }, "고치러 가기 →") : null),
      el("div", { class: "msg" }, e.msg),
      e.hint ? el("div", { class: "fix" }, el("b", {}, "이렇게 고치세요 "), e.hint) : null,
      el("div", { class: "raw pro-only" }, e.raw || e.where));
    for (const e of r.errors || []) box.append(issue("err", e));
    for (const w of r.warnings || []) box.append(issue("warn", w));
  }

  // ------------------------------------------------------------------ 렌더 작업 + 진행 상태
  const STAGES = ["목소리 합성", "화면 렌더링", "합치기", "검증"];
  async function startBuild(kind) {
    if (!state.pid) return;
    if (state.dirty) { const ok = await save(); if (!ok || state.dirty) return; }
    if (state.lastCheck && !state.lastCheck.ok && !confirm(`고칠 곳이 ${state.lastCheck.errors.length}개 있습니다 (문제점 탭). 그래도 렌더할까요?`)) { switchTab("check"); return; }
    const body = { preview: kind !== "final" };
    if (kind === "partial") {
      const seg = state.doc.segments[state.sel];
      if (!seg) { toast("먼저 장면을 하나 만들어 주세요", "bad"); return; }
      body.segments = [seg.id];
    }
    try {
      const job = await api(`/api/projects/${state.pid}/build`, { method: "POST", body });
      $("#logBox").textContent = ""; state.logOffset = 0; state.stage = 0;
      attachJob(job);
      toast(kind === "partial" ? `‘${body.segments[0]}’ 장면 미리보기 시작 — 끝나면 오른쪽 영상 탭에 나타납니다` : kind === "final" ? "최종 영상 만들기 시작 (몇 분 걸립니다)" : "전체 미리보기 시작");
    } catch (e) { toast(e.message, "bad"); }
  }

  function attachJob(job) {
    state.job = job; state.logOffset = 0; state.stage = 0; $("#logBox").textContent = "";
    updateJobStatus(job);
    clearInterval(state.pollTimer);
    state.pollTimer = setInterval(pollJob, 1500);
    pollJob();
  }

  async function pollJob() {
    if (!state.job) return;
    try {
      const r = await api(`/api/jobs/${state.job.id}?offset=${state.logOffset}`);
      if (r.log) {
        const lb = $("#logBox"); lb.textContent += r.log; lb.scrollTop = lb.scrollHeight; state.logOffset = r.offset;
        for (const m of r.log.matchAll(/\[(\d)\/4\]/g)) state.stage = Math.max(state.stage, Number(m[1]));
      }
      state.job = r.job; updateJobStatus(r.job);
      if (r.job.status !== "running") {
        clearInterval(state.pollTimer); state.pollTimer = null;
        const outs = await api(`/api/projects/${state.pid}/outputs`);
        state.outputs = outs; renderOutputs();
        if (r.job.status === "done") { renderSegList(); renderSegEditor(); }
        if (r.job.status === "done") { toast(r.job.kind === "final" ? "최종 영상 완성 ✓ — 검증 탭에서 결과를 확인하세요" : "미리보기 완성 ✓ — 오른쪽 영상 탭", "ok"); switchTab(r.job.kind === "final" ? "verify" : "video"); }
        else if (r.job.status === "failed") { toast("렌더에 실패했습니다 — 로그 탭의 마지막 줄을 확인하세요", "bad"); switchTab("log"); }
        loadProjects();
      }
    } catch (e) { clearInterval(state.pollTimer); toast(e.message, "bad"); }
  }

  function updateJobStatus(job) {
    const s = $("#jobStatus");
    const running = job && job.status === "running";
    $("#btnCancel").classList.toggle("hidden", !running);
    for (const id of ["btnPartial", "btnPreview", "btnFinal"]) $("#" + id).disabled = !!running;
    s.innerHTML = ""; s.className = "progress" + (job ? " " + job.status : "");
    if (!job) { updateNextHint(); return; }
    const label = { preview: "전체 미리보기", final: "최종 영상", partial: "장면 미리보기" }[job.kind] || job.kind;
    const stage = Math.max(1, state.stage || 1);
    const elapsed = job.started ? Math.max(0, (Date.now() - new Date(job.started).getTime()) / 1000) : 0;
    const bar = el("div", { class: "bar" }, el("i", { class: running ? "anim" : "", style: `width:${running ? Math.round((stage - 1) / 4 * 100 + 12) : 100}%` }), el("span", { class: "ticks" }, el("i"), el("i"), el("i"), el("i")));
    if (running) {
      s.append(el("div", { class: "lbl" }, el("b", {}, `${label} 만드는 중`), `${stage}/4 ${STAGES[stage - 1]} · ${fmtClock(elapsed)}`), bar,
        el("div", { class: "stages" }, ...STAGES.map((n, k) => el("span", { class: k + 1 < stage ? "ok" : k + 1 === stage ? "on" : "" }, n))));
    } else if (job.status === "done") s.append(el("div", { class: "lbl done" }, el("b", {}, `✓ ${label} 완성`), job.finished ? job.finished.slice(11, 16) : ""), bar);
    else if (job.status === "failed") s.append(el("div", { class: "lbl failed" }, el("b", {}, `✗ ${label} 실패`), "로그 탭 확인"), bar);
    else s.append(el("div", { class: "lbl" }, el("b", {}, "중지됨")));
    updateNextHint();
  }
  /** 상단 ①②③ 중 지금 권하는 다음 단계를 표시. */
  function updateNextHint() {
    const o = state.outputs || {}; const full = o.full || {}, part = o.partial || {};
    for (const id of ["btnPartial", "btnPreview", "btnFinal"]) $("#" + id).classList.remove("next");
    if (!state.doc) return;
    const next = !(part.preview || full.preview || full.final) ? "btnPartial" : !(full.preview || full.final) ? "btnPreview" : "btnFinal";
    $("#" + next).classList.add("next");
  }

  // ------------------------------------------------------------------ 산출물 패널
  function renderOutputs() {
    const o = state.outputs || {};
    const full = o.full || {}, part = o.partial || {};
    const vs = $("#videoSource");
    const prev = vs.value;
    vs.innerHTML = "";
    const opts = [];
    if (full.final) opts.push(["final", "최종 영상", full.final]);
    if (full.preview) opts.push(["preview", "전체 미리보기 (480p)", full.preview]);
    if (part.preview) opts.push(["partial", "장면 미리보기 (선택 장면만)", part.preview]);
    if (part.final) opts.push(["partial_final", "장면 렌더 (최종 해상도)", part.final]);
    for (const [k, label, url] of opts) vs.append(el("option", { value: k, "data-url": url }, label));
    const video = $("#video");
    $("#videoEmpty").classList.toggle("hidden", !!opts.length);
    video.classList.toggle("hidden", !opts.length);
    vs.parentElement.classList.toggle("hidden", !opts.length);
    if (opts.length) {
      vs.value = opts.some((x) => x[0] === prev) ? prev : opts[0][0];
      const url = vs.selectedOptions[0].dataset.url;
      if (video.getAttribute("src") !== url) video.src = url;
      $("#videoInfo").textContent = "";
    } else { video.removeAttribute("src"); }
    vs.onchange = () => { video.src = vs.selectedOptions[0].dataset.url; renderOutputs(); };

    const chips = $("#segChips"); chips.innerHTML = "";
    const tl = (vs.value?.startsWith("partial") ? part.timeline : full.timeline) || {};
    for (const s of tl.segments || []) {
      chips.append(el("span", { class: "chip", title: "이 장면부터 재생", onclick: () => { video.currentTime = s.start; video.play().catch(() => {}); } }, s.id, el("small", {}, fmtClock(s.start))));
    }
    const sb = $("#storyboard");
    if (full.storyboard) { sb.src = full.storyboard; sb.classList.remove("hidden"); $("#storyboardHint").textContent = "장면마다 대표 화면 한 장씩. 전체 흐름을 한눈에 확인하는 용도입니다."; }
    else { sb.removeAttribute("src"); $("#storyboardHint").textContent = "전체 미리보기/최종 영상을 만들면 장면별 대표 화면이 여기에 표시됩니다."; }

    const vb = $("#verifyBox"); vb.innerHTML = "";
    const rep = full.verify_report;
    if (rep) {
      const okN = rep.checks.filter((c) => c.ok).length;
      vb.append(el("div", { class: "sum" }, `${rep.ok ? "✅" : "❌"} ${okN} / ${rep.checks.length} 항목 통과 — ${rep.video}`));
      const t = el("table");
      for (const c of rep.checks) t.append(el("tr", {}, el("td", { class: c.ok ? "ok" : "bad" }, c.ok ? "통과" : "실패"), el("td", {}, c.name), el("td", { class: "hint" }, c.detail || "")));
      vb.append(t);
    } else vb.append(el("p", { class: "hint" }, "최종 영상을 만들면 21항목(길이·자막 동기화·음량·화면 잘림 등) 자동 검증 결과가 여기에 표시됩니다."));
    updateNextHint();
  }

  // ------------------------------------------------------------------ 타임라인
  async function loadTiming() {
    const btn = $("#btnTiming"); btn.disabled = true; btn.textContent = "목소리 합성 중…";
    try { state.timing = await api(`/api/projects/${state.pid}/timing`); renderTimeline(); }
    catch (e) { toast(e.message, "bad"); }
    btn.disabled = false; btn.textContent = "문장 시간 재기 (TTS)";
  }
  function renderTimeline() {
    const box = $("#timelineBox"); box.innerHTML = "";
    const t = state.timing;
    if (!t) { box.append(el("p", { class: "hint" }, "대본을 목소리로 합성해 장면·문장 길이를 잽니다 (한 번 재면 캐시되어 다음부터 즉시).")); return; }
    const total = t.total || 1;
    box.append(el("p", { class: "hint" }, `총 예상 길이 ≈ ${t.total.toFixed(1)}초 (${(t.total / 60).toFixed(1)}분) — 동작이 대본보다 길면 실제 영상은 더 길어집니다`));
    t.segments.forEach((s, i) => {
      const dur = s.end - s.start;
      const bar = el("div", { class: "bar" + (i === state.sel ? " on" : ""), style: `width:${Math.max(18, (dur / total) * 100)}%`,
        onclick: () => { state.sel = i; showPane("seg"); renderSegList(); renderSegEditor(); renderTimeline(); } },
        el("span", { class: "lab" }, s.id), el("span", { class: "dur" }, `${dur.toFixed(1)}s`));
      for (const sn of s.sentences) {
        bar.append(el("span", { class: "tick", style: `left:${(sn.start / Math.max(dur, 0.1)) * 100}%`, title: `${sn.i}번째 문장 (${sn.start.toFixed(1)}s) ${sn.text}`,
          onclick: (e) => { e.stopPropagation(); navigator.clipboard?.writeText("s" + sn.i); toast(`s${sn.i} 복사됨`); } }, "s" + sn.i));
      }
      box.append(bar);
    });
  }

  // ------------------------------------------------------------------ 탭/모달/이력/도움말/투어
  function switchTab(name) {
    $$("#preview .tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
    $$("#preview .tab").forEach((t) => t.classList.toggle("on", t.id === "tab-" + name));
  }
  function modal(content, wide = false) {
    const m = $("#modal"); const b = $("#modalBody"); b.innerHTML = ""; b.className = "modal-body" + (wide ? " wide" : ""); b.append(content); m.classList.remove("hidden");
    m.onclick = (e) => { if (e.target === m) m.classList.add("hidden"); };
  }
  const closeModal = () => $("#modal").classList.add("hidden");

  async function showHistory() {
    const items = await api(`/api/projects/${state.pid}/history`);
    const ul = el("ul");
    if (!items.length) ul.append(el("li", {}, "저장 이력이 없습니다. 저장할 때마다 이전 버전이 여기에 쌓입니다."));
    for (const h of items) {
      ul.append(el("li", {}, el("span", {}, `${h.time}  (${(h.size / 1024).toFixed(1)} KB)`),
        el("button", { class: "mini", onclick: async () => {
          if (!confirm("이 시점으로 되돌릴까요? (현재 파일도 이력에 보관됩니다)")) return;
          await api(`/api/projects/${state.pid}/history/${h.name}/restore`, { method: "POST" });
          closeModal(); setDirty(false); await openProject(state.pid); toast("되돌렸습니다", "ok");
        } }, "이 버전으로")));
    }
    modal(el("div", {}, el("h3", {}, "저장 이력 (최근 30개)"), ul));
  }

  function newProjectDialog() {
    const idIn = el("input", { placeholder: "폴더 이름 — 영문 소문자/숫자/밑줄 (예: 2026_suneung_q22)", style: "width:100%" });
    const titleIn = el("input", { placeholder: "영상 제목 (예: 2026학년도 수능 수학 22번)", style: "width:100%;margin-top:8px" });
    titleIn.addEventListener("input", () => { if (!idIn._touched) idIn.value = titleIn.value.toLowerCase().replace(/학년도/g, "").replace(/[^a-z0-9가-힣]+/g, "_").replace(/[가-힣]+/g, "").replace(/^_+|_+$/g, "").slice(0, 40); });
    idIn.addEventListener("input", () => { idIn._touched = true; });
    const btn = el("button", { class: "accent", style: "margin-top:12px", onclick: async () => {
      try {
        await api("/api/projects", { method: "POST", body: { id: idIn.value.trim(), title: titleIn.value.trim() || "새 영상" } });
        closeModal(); await loadProjects(); await openProject(idIn.value.trim()); toast("프로젝트를 만들었습니다 — 예시 장면이 들어 있으니 고쳐 쓰세요", "ok");
      } catch (e) { toast(e.message, "bad"); }
    } }, "만들기");
    modal(el("div", {}, el("h3", {}, "새 프로젝트"), titleIn, idIn, el("p", { class: "hint" }, "projects/<폴더 이름>/project.yaml 이 칠판 스타일 예시로 만들어집니다. 직접 만든 애니메이션 함수는 같은 폴더의 hooks.py 에 두면 ‘내가 만든 함수’ 동작에서 쓸 수 있습니다."), btn));
    titleIn.focus();
  }

  function showHelp() {
    const g = (t, c, d) => [el("dt", {}, t, c ? el("code", {}, c) : null), el("dd", {}, d)];
    const body = el("div", { class: "help" },
      el("h3", {}, "Explainer Studio 사용법"),
      el("p", { class: "hint" }, "대본을 쓰고 → 문장에 동작을 붙이고 → 미리보기로 확인하고 → 최종 영상을 만듭니다."),
      el("div", { class: "steps4" },
        el("div", {}, el("b", {}, "1. 장면 만들기"), "왼쪽 ‘＋ 장면’. 장면 하나 = 영상의 한 토막 (문제 읽기, 풀이 1단계, …)"),
        el("div", {}, el("b", {}, "2. 대본 쓰기"), "① 칸에 말할 내용을. 마침표로 문장을 끊으면 문장별로 동작을 맞출 수 있어요. ▶ 듣기로 실제 시각을 잽니다"),
        el("div", {}, el("b", {}, "3. 동작 붙이기"), "② 문장 줄의 ‘＋ 여기서’ 또는 ③ ‘＋ 동작 추가’. 판서·식 전개·그래프·강조 등을 고릅니다"),
        el("div", {}, el("b", {}, "4. 확인 → 완성"), "상단 ① 이 장면 미리보기(수십 초) → ② 전체 미리보기 → ③ 최종 영상. 결과는 오른쪽 패널에")),
      el("h4", {}, "용어"),
      el("dl", {},
        ...g("장면", "segment", "대본 한 덩어리 + 그동안 칠판에서 일어나는 동작들. 순서대로 이어져 한 편이 됩니다."),
        ...g("동작", "action", "칠판에서 일어나는 한 가지 일: 판서, 식 전개, 그래프 그리기, 강조, 카메라 이동 …"),
        ...g("시작 시점", "at", "동작이 언제 시작하는지. ‘n번째 문장’ 을 고르면 그 문장을 읽기 시작할 때 실행. 비우면 앞 동작이 끝난 뒤 이어서."),
        ...g("길이", "run_time", "동작 애니메이션이 몇 초 동안 진행되는지. 비우면 동작별 기본값."),
        ...g("칠판 칸", "section", "칠판은 왼쪽→오른쪽으로 이어진 칸들. ‘칠판 칸 이동’ 동작으로 카메라가 다음 칸으로 갑니다. 칸은 ⚙ 영상 설정에서 만듭니다."),
        ...g("식 전개", "derive", "여러 줄의 식 변형을 | 로 조각내어 쓰면, 바뀐 조각만 강조되어 날아가는 애니메이션이 됩니다."),
        ...g("이름 (id)", "id", "그래프·점·판서에 붙이는 이름. 나중에 ‘강조’, ‘흐리게’, ‘카메라 줌’ 에서 이 이름으로 가리킵니다."),
        ...g("내가 만든 함수", "custom", "프로젝트 폴더 hooks.py 에 파이썬 함수를 만들면 동작으로 쓸 수 있습니다."),
        ...g("수식", "LaTeX", "x^{2}, \\dfrac{a}{b}, \\sqrt{x} 처럼 씁니다. 입력란 아래에 조판 결과가 바로 보입니다. 글과 섞을 때는 $…$ 로 감싸요.")),
      el("h4", {}, "단축키"),
      el("div", { class: "keys" }, el("span", {}, el("kbd", {}, "Ctrl+S"), " 저장"), el("span", {}, el("kbd", {}, "Ctrl+Z"), " 되돌리기"), el("span", {}, el("kbd", {}, "Ctrl+Y"), " 다시하기"), el("span", {}, el("kbd", {}, "F1"), " 도움말")),
      el("h4", {}, "고급 모드"),
      el("p", { class: "hint" }, "상단 ‘고급’ 을 켜면 내부 이름(YAML 키, 동작 코드), JSON 원문 편집, YAML 전체 보기가 함께 나타납니다. 문서(docs/guide_suneung_calc30.md)와 대조할 때 켜세요."),
      el("div", { class: "row", style: "margin-top:14px" }, el("button", { class: "ghost", onclick: () => { closeModal(); startTour(true); } }, "화면 안내 다시 보기"), el("span", { class: "spacer" }), el("button", { class: "accent", onclick: closeModal }, "닫기")));
    modal(body, true);
  }

  const TOUR = [
    { sel: "#sidebar", title: "① 장면 목록", text: "영상은 장면들이 순서대로 이어진 것입니다. 클릭해서 고르고, 드래그로 순서를 바꾸고, ＋ 장면으로 추가합니다." },
    { sel: "#segEditor .block.narr", title: "② 대본", text: "말할 내용을 씁니다. 마침표로 문장을 끊으세요 — 문장마다 동작을 붙일 수 있습니다. ▶ 듣기로 목소리를 확인하고 문장 시각을 잽니다." },
    { sel: "#segEditor .block.syncb", title: "③ 문장에 동작 맞추기", text: "줄 하나가 문장 하나. 줄 위에 마우스를 올리면 나오는 ‘＋ 여기서’ 로 그 문장에 맞춰 동작을 추가합니다. 칩을 누르면 그 동작의 설정으로 이동." },
    { sel: "#segEditor .cards", title: "④ 동작 카드", text: "카드를 누르면 세부 설정이 열립니다. 수식은 입력란 아래에 바로 조판되어 보이고, 실행 전/후 화면도 (렌더한 뒤에는) 함께 보입니다." },
    { sel: ".flow", title: "⑤ 확인하고 완성하기", text: "① 이 장면만 빨리 미리보기(수십 초) → ② 전체 미리보기 → ③ 최종 영상. 노란 테두리가 지금 권하는 다음 단계입니다." },
    { sel: "#preview", title: "⑥ 결과 패널", text: "만든 영상·장면 그림·검증 결과·문제점이 여기에. 문제점의 항목을 클릭하면 그 자리로 바로 이동합니다. 궁금하면 상단 ? 를 누르세요." },
  ];
  function startTour(force = false) {
    if (!force && LS.get("tour.v1", false)) return;
    const root = $("#tour"); root.innerHTML = ""; root.classList.remove("hidden");
    let k = 0;
    const done = () => { root.classList.add("hidden"); root.innerHTML = ""; LS.set("tour.v1", true); };
    const show = () => {
      root.innerHTML = "";
      while (k < TOUR.length && !document.querySelector(TOUR[k].sel)) k++;
      if (k >= TOUR.length) return done();
      const step = TOUR[k]; const target = document.querySelector(step.sel);
      target.scrollIntoView({ block: "nearest" });
      const r = target.getBoundingClientRect();
      const spot = el("div", { class: "spot", style: `left:${r.left - 4}px;top:${r.top - 4}px;width:${r.width + 8}px;height:${r.height + 8}px` });
      const bubble = el("div", { class: "bubble" }, el("h4", {}, step.title), el("p", {}, step.text),
        el("div", { class: "nav" }, el("span", { class: "hint" }, `${k + 1} / ${TOUR.length}`),
          el("button", { class: "ghost mini", onclick: done }, "건너뛰기"),
          k > 0 ? el("button", { class: "mini", onclick: () => { k--; show(); } }, "이전") : null,
          el("button", { class: "accent mini", onclick: () => { k++; if (k >= TOUR.length) done(); else show(); } }, k + 1 >= TOUR.length ? "시작하기" : "다음")));
      root.append(el("div", { class: "dimmer", onclick: done }), spot, bubble);
      // 말풍선 위치: 대상 오른쪽 → 안 되면 왼쪽 → 아래
      const W = 320, H = 150, vw = innerWidth, vh = innerHeight;
      let left = r.right + 14, top = Math.max(10, Math.min(r.top, vh - H - 10));
      if (left + W > vw - 10) left = r.left - W - 14;
      if (left < 10) { left = Math.max(10, Math.min(r.left, vw - W - 10)); top = r.bottom + 14 < vh - H ? r.bottom + 14 : Math.max(10, r.top - H - 14); }
      bubble.style.left = left + "px"; bubble.style.top = top + "px";
    };
    show();
  }

  function setPro(v) {
    state.pro = v; LS.set("pro", v); document.body.classList.toggle("pro", v); $("#proMode").checked = v;
    if (state.doc) { renderSegEditor(); }
  }

  // ------------------------------------------------------------------ 이벤트
  function bind() {
    $("#projectSelect").addEventListener("change", (e) => openProject(e.target.value));
    $("#btnNew").addEventListener("click", newProjectDialog);
    $("#btnSave").addEventListener("click", save);
    $("#btnUndo").addEventListener("click", undo);
    $("#btnRedo").addEventListener("click", redo);
    $("#btnValidate").addEventListener("click", () => validate(false));
    $("#btnTex").addEventListener("click", () => validate(true));
    $("#btnPartial").addEventListener("click", () => startBuild("partial"));
    $("#btnPreview").addEventListener("click", () => startBuild("preview"));
    $("#btnFinal").addEventListener("click", () => { if (confirm("최종 해상도로 렌더합니다. 길이에 따라 몇 분~수십 분 걸릴 수 있어요. 시작할까요?")) startBuild("final"); });
    $("#btnCancel").addEventListener("click", async () => { if (state.job) { await api(`/api/jobs/${state.job.id}/cancel`, { method: "POST" }); toast("중지를 요청했습니다"); } });
    $("#btnAddSeg").addEventListener("click", addSegment);
    $("#tabSettings").addEventListener("click", () => showPane("settings"));
    $("#tabYaml").addEventListener("click", () => showPane("yaml"));
    $("#btnHistory").addEventListener("click", showHistory);
    $("#btnHelp").addEventListener("click", showHelp);
    $("#proMode").addEventListener("change", (e) => setPro(e.target.checked));
    $("#yamlText").addEventListener("input", () => { state.yamlDirty = true; setDirty(true); });
    $("#btnYamlApply").addEventListener("click", async () => {
      try {
        const r = await api("/api/yaml/parse", { method: "POST", body: { yaml: $("#yamlText").value } });
        state.past.push(JSON.stringify(state.doc)); state.future = [];
        state.doc = r.doc; state.snap = JSON.stringify(state.doc); state.yamlText = $("#yamlText").value; state.sel = Math.min(state.sel, Math.max(0, (state.doc.segments || []).length - 1));
        renderSegList(); renderSegEditor(); renderSettings(); showPane("seg"); updateUndoButtons(); toast("YAML 을 폼에 반영했습니다 (저장은 별도)", "ok");
      } catch (e) { toast(e.message, "bad"); }
    });
    $$("#preview .tabs button").forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));
    $("#btnTiming").addEventListener("click", loadTiming);
    document.addEventListener("keydown", (e) => {
      const inField = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "");
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
      else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === "z" && !inField) { e.preventDefault(); undo(); }
      else if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === "y" || (e.shiftKey && e.key.toLowerCase() === "z")) && !inField) { e.preventDefault(); redo(); }
      else if (e.key === "F1") { e.preventDefault(); showHelp(); }
      else if (e.key === "Escape") { closeModal(); }
    });
    window.addEventListener("beforeunload", (e) => { if (state.dirty) { e.preventDefault(); e.returnValue = ""; } });
  }

  // ------------------------------------------------------------------ 시작
  async function init() {
    bind();
    setPro(!!state.pro);
    state.catalog = await api("/api/actions");
    state.catalogByName = Object.fromEntries(state.catalog.map((a) => [a.name, a]));
    await loadProjects();
    const want = location.hash.slice(1);
    const first = state.projects.find((p) => p.id === want) || state.projects[0];
    if (first) await openProject(first.id);
    else { $("#segEditor").append(el("div", { class: "empty" }, el("div", { class: "big" }, "👋"), el("p", {}, "아직 프로젝트가 없습니다."), el("div", { class: "actions" }, el("button", { class: "accent", onclick: newProjectDialog }, "＋ 첫 프로젝트 만들기")))); }
    // KaTeX 가 늦게 로드되면 카드 요약/미리보기를 한 번 다시 그린다
    if (!hasKatex()) { const t = setInterval(() => { if (hasKatex()) { clearInterval(t); if (state.doc) renderSegEditor(); } }, 400); setTimeout(() => clearInterval(t), 15000); }
    setTimeout(() => startTour(false), 600);
  }
  init().catch((e) => toast("초기화 실패: " + e.message, "bad"));
})();
