/* Explainer Studio – 프론트엔드 (외부 의존성 없음) */
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
      else if (v !== undefined && v !== null) n.setAttribute(k, v);
    }
    for (const c of children.flat()) if (c !== null && c !== undefined) n.append(c.nodeType ? c : document.createTextNode(String(c)));
    return n;
  };

  const state = {
    projects: [], pid: null, doc: null, yamlText: "", yamlDirty: false, dirty: false,
    catalog: [], catalogByName: {}, hooks: [], sel: 0, outputs: null, job: null, logOffset: 0,
    timing: null, pollTimer: null, rawOpen: new Set(),
    expanded: new Set(),      // 펼쳐진 액션 카드
    sentences: {},            // seg id → {exact, sentences:[{i,text,start?}], narr}  (서버: TTS 캐시 기준 실제 문장 경계)
  };

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
    clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), 3200);
  }

  function setDirty(v) {
    state.dirty = v;
    $("#dirtyDot").classList.toggle("on", v);
  }

  // ------------------------------------------------------------------ 값 표시/파싱
  const fmtVal = (v) => (typeof v === "string" ? v : JSON.stringify(v));
  function parseVal(s) {
    const t = s.trim();
    if (t === "") return undefined;
    if (/^(true|false|null)$/.test(t)) return JSON.parse(t);
    if (/^-?\d+(\.\d+)?$/.test(t)) return Number(t);
    if (/^[\[{"]/.test(t)) { try { return JSON.parse(t); } catch (_) { return s; } }
    return s;
  }
  const splitSentences = (text) => (text || "").trim().split(/(?<=[.?!…])\s+/).filter(Boolean);
  const normNarr = (t) => (t || "").split(/\s+/).filter(Boolean).join(" ");
  // 세그먼트의 문장 목록: 같은 내레이션이 TTS 캐시에 있으면 엔진이 실제로 끊어 읽은 경계(exact), 아니면 문장부호 추정
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

  // ------------------------------------------------------------------ 프로젝트 로드
  async function loadProjects() {
    state.projects = await api("/api/projects");
    const sel = $("#projectSelect");
    sel.innerHTML = "";
    for (const p of state.projects) {
      sel.append(el("option", { value: p.id }, `${p.title}  (${p.id})${p.running ? "  ⏳" : ""}`));
    }
    if (state.pid) sel.value = state.pid;
  }

  async function openProject(pid) {
    if (state.dirty && !confirm("저장하지 않은 변경이 있습니다. 버릴까요?")) { $("#projectSelect").value = state.pid; return; }
    const data = await api(`/api/projects/${pid}`);
    state.pid = pid; state.doc = data.doc; state.yamlText = data.yaml; state.yamlDirty = false;
    state.hooks = data.hooks || []; state.outputs = data.outputs; state.sel = 0; state.timing = null;
    state.rawOpen.clear(); state.sentences = {}; setSentences(data.sentences, data.doc);
    setDirty(false);
    if (data.parse_error) toast("YAML 파싱 오류: " + data.parse_error + " — YAML 탭에서 고치세요", "bad");
    if (!state.doc) { state.doc = { meta: { id: pid, title: pid }, segments: [] }; }
    if (!Array.isArray(state.doc.segments)) state.doc.segments = [];
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
  }

  // ------------------------------------------------------------------ 액션 표시 정보 (아이콘·한글 이름·분류 색)
  const CAT_COLOR = {
    "카드·전환": "#b48cff", "문제": "#7cc4ff", "칠판 판서": "#ffd23f", "식 전개": "#ff9f43",
    "그래프": "#5ad48a", "보드(panel 스타일)": "#4fd1c5", "사용자 정의": "#ff7ab6",
  };
  const ACTION_META = {
    title_card: ["제목 카드", "▣"], end_card: ["마무리 카드", "▤"], section: ["섹션", "▭"], wait: ["대기", "⏸"],
    clear: ["지우기", "⌫"], fade: ["사라짐", "◌"], dim: ["흐리게", "◐"], undim: ["되돌리기", "◑"], highlight: ["강조", "✦"],
    problem: ["문제 전문", "≣"], problem_focus: ["읽는 줄 강조", "▶"], problem_dock: ["문제 축소", "⬒"], answer: ["정답", "✔"],
    caption: ["캡션 메모", "❝"], goto: ["칸 이동", "➜"], write: ["판서", "✍"], space: ["여백", "␣"], camera: ["카메라", "◎"],
    derive: ["식 전개", "∑"], step: ["전개 단계", "↳"], axes: ["좌표축", "┼"], plot: ["그래프", "∿"], line: ["직선", "╱"],
    vline: ["세로선", "│"], point: ["점", "•"], points: ["점들", "∴"], polygon: ["다각형", "⬠"], segment: ["선분", "—"],
    arrow: ["화살표", "→"], guides: ["보조선", "⌐"], translate_copy: ["평행이동 복사", "⇢"], reflect: ["대칭이동", "⇋"],
    label: ["라벨", "🏷"], board_init: ["보드 만들기", "▦"], board_write: ["보드 쓰기", "▦"], board_replace: ["보드 바꾸기", "▦"],
    board_highlight: ["보드 강조", "▦"], board_clear: ["보드 지우기", "▦"], board_title: ["보드 제목", "▦"], custom: ["사용자 함수", "⚙"],
  };
  const actLabel = (name) => (ACTION_META[name] || [name])[0];
  const actIcon = (name) => (ACTION_META[name] || [null, "▪"])[1];
  const actColor = (name) => CAT_COLOR[state.catalogByName[name]?.category] || "#8b93a7";
  const short = (s, n = 60) => { s = String(s ?? ""); return s.length > n ? s.slice(0, n - 1) + "…" : s; };
  const stripTex = (s) => String(s ?? "").replace(/\\(tfrac|dfrac|frac)\{([^}]*)\}\{([^}]*)\}/g, "$2/$3").replace(/\\mathrm\{([^}]*)\}/g, "$1")
    .replace(/\\(quad|qquad|;|,|!)/g, " ").replace(/\\(Rightarrow|to|xrightarrow)/g, "→").replace(/\\(times|cdot)/g, "×").replace(/\\(log|therefore|checkmark)/g, (m) => ({ "\\log": "log", "\\therefore": "∴", "\\checkmark": "✓" })[m])
    .replace(/\\[a-zA-Z]+/g, (m) => m.slice(1)).replace(/[{}$]/g, "").replace(/\s+/g, " ").trim();

  /** 카드 머리에 보일 한 줄 요약: "이 액션이 무엇을 하는지" 가 파라미터 표 없이도 읽히게. */
  function summarize(act) {
    const a = act, j = (v) => (Array.isArray(v) ? v.join(", ") : v === undefined ? "" : String(v));
    switch (a.do) {
      case "goto": return `→ ${a.section ?? "?"} 칸`;
      case "title_card": case "end_card": return short(a.title ?? "");
      case "write": return short(stripTex(a.text ?? a.tex ?? (a.lines || []).join("  /  ")));
      case "caption": return short(stripTex(a.text ?? a.tex ?? ""));
      case "problem": return `${a.title ?? ""} · ${(a.lines || []).length}줄${a.choices ? ` · 보기 ${a.choices.length}개` : ""}`;
      case "problem_focus": return `${(a.index ?? 0) + 1}번째 줄`;
      case "answer": return a.tex ? stripTex(a.tex) : a.choice ? `보기 ${a.choice}번에 동그라미` : "";
      case "derive": { const st = a.steps || []; return `${a.id ?? "d"} · ${st.length}단계` + (st[0] ? ` — ${short(stripTex((st[0].parts || [st[0].tex]).join(" ")), 40)}` : ""); }
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
      case "highlight": return `${j(a.ids)}  · ${a.mode ?? "indicate"}`;
      case "dim": case "undim": case "fade": return j(a.ids);
      case "camera": return a.reset ? "원래 뷰로" : a.sections ? `칸 ${j(a.sections)} 전체` : a.ids ? `${j(a.ids)} 이 보이게` : a.focus ?? (a.pos ? `(${j(a.pos)})` : "");
      case "custom": { const ps = Object.entries(a).filter(([k]) => !["do", "fn", "at", "run_time"].includes(k)).slice(0, 3).map(([k, v]) => `${k}=${short(fmtVal(v), 18)}`); return `${a.fn}(${ps.join(", ")})`; }
      case "wait": return `${a.seconds ?? 1}초`;
      case "label": return short(stripTex(a.text ?? a.tex ?? ""));
      default: { const ps = Object.entries(a).filter(([k, v]) => !["do", "at", "run_time"].includes(k) && (typeof v === "string" || typeof v === "number")).slice(0, 2); return ps.map(([k, v]) => `${k}: ${short(String(v), 24)}`).join(" · "); }
    }
  }
  const atText = (at) => (at === undefined || at === null || at === "" ? "" : typeof at === "number" ? `${at}s` : String(at));

  // ------------------------------------------------------------------ 세그먼트 목록
  function segDuration(seg) {
    const info = state.sentences[seg.id];
    if (info && info.exact && info.narr === normNarr(seg.narration) && info.sentences.length) return info.sentences[info.sentences.length - 1].end;
    return null;
  }
  function renderSegList() {
    const ul = $("#segList");
    ul.innerHTML = "";
    let t0 = Number(state.doc.meta?.intro_silence ?? 0.6);
    state.doc.segments.forEach((seg, i) => {
      const acts = seg.actions || [];
      const dur = segDuration(seg);
      const nS = sentencesFor(seg).list.length;
      const bar = el("div", { class: "mix" });
      for (const a of acts) bar.append(el("i", { style: `background:${actColor(a.do)}`, title: `${actLabel(a.do)} ${summarize(a)}` }));
      const li = el("li", { class: i === state.sel ? "on" : "", draggable: "true",
        onclick: () => { state.sel = i; showPane("seg"); renderSegList(); renderSegEditor(); } },
        el("span", { class: "n" }, String(i + 1)),
        el("div", { class: "body" },
          el("div", { class: "id" }, seg.id || "(id 없음)"),
          el("div", { class: "meta" }, `${nS}문장 · ${acts.length}액션` + (dur !== null ? ` · ${dur.toFixed(0)}s` : "")),
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

  function touched() { setDirty(true); state.yamlDirty = false; }

  // ------------------------------------------------------------------ 세그먼트 편집기
  function renderSegEditor() {
    const pane = $("#segEditor");
    pane.innerHTML = "";
    const seg = state.doc.segments[state.sel];
    if (!seg) {
      pane.append(el("p", { class: "hint" }, "세그먼트가 없습니다. 왼쪽 + 버튼으로 추가하세요."));
      return;
    }
    seg.actions = seg.actions || [];

    // 머리: 번호 배지 + id(인라인 편집) + 길이 + 버튼
    const idIn = el("input", { class: "seg-id", value: seg.id || "", placeholder: "세그먼트 id (예: read_problem)", spellcheck: "false" });
    idIn.addEventListener("change", () => { seg.id = idIn.value.trim(); touched(); renderSegList(); });
    const padIn = el("input", { class: "seg-pad", value: seg.pad ?? "", placeholder: `여백 ${state.doc.meta?.segment_pad ?? 0.5}s`, title: "이 세그먼트 뒤의 여백(초). 비우면 meta.segment_pad" });
    padIn.addEventListener("change", () => { const n = parseVal(padIn.value); if (n === undefined) delete seg.pad; else seg.pad = n; touched(); });
    const dur = segDuration(seg);
    const head = el("div", { class: "seg-head" },
      el("span", { class: "badge" }, String(state.sel + 1)),
      el("div", { class: "titles" }, idIn,
        el("div", { class: "hint" }, `${state.sel + 1} / ${state.doc.segments.length} 번째 세그먼트` + (dur !== null ? ` · 내레이션 ${dur.toFixed(1)}s` : "") + ` · 액션 ${seg.actions.length}개`)),
      padIn,
      el("span", { class: "spacer" }),
      el("button", { class: "ghost mini", title: "위로", onclick: () => moveSeg(-1) }, "↑"),
      el("button", { class: "ghost mini", title: "아래로", onclick: () => moveSeg(1) }, "↓"),
      el("button", { class: "ghost mini", onclick: () => dupSeg() }, "복제"),
      el("button", { class: "danger mini", onclick: () => delSeg() }, "삭제"));
    pane.append(head);

    // 1) 내레이션
    const narr = el("section", { class: "block" });
    const ta = el("textarea", { placeholder: "내레이션. 문장(., ?, !)으로 끊으면 아래 표에서 문장별로 애니메이션을 맞출 수 있습니다." });
    ta.value = seg.narration || "";
    const audio = el("audio", { controls: "", class: "hidden", style: "height:28px" });
    const btnTts = el("button", { class: "ghost mini", onclick: async () => {
      btnTts.disabled = true; btnTts.textContent = "합성 중…";
      try {
        const r = await api("/api/tts", { method: "POST", body: { text: ta.value, voice: seg.voice || state.doc.meta.voice || "ko-KR-InJoonNeural", rate: seg.rate || state.doc.meta.rate || "+0%" } });
        state.sentences[seg.id] = { exact: true, sentences: r.sentences, narr: normNarr(ta.value) };
        audio.src = r.audio_url; audio.classList.remove("hidden"); audio.play().catch(() => {});
        toast(`내레이션 ${r.duration.toFixed(1)}초, ${r.sentences.length}문장`);
        renderSync(); renderCards(); renderSegList();
      } catch (e) { toast(e.message, "bad"); }
      btnTts.disabled = false; btnTts.textContent = "▶ 듣기 · 문장 타이밍";
    } }, "▶ 듣기 · 문장 타이밍");
    narr.append(el("div", { class: "block-head" }, el("h3", {}, "① 내레이션"), el("span", { class: "hint" }, "이 글이 TTS 로 읽힙니다"), el("span", { class: "spacer" }), audio, btnTts), ta);
    ta.addEventListener("input", () => { seg.narration = ta.value; touched(); renderSync(); });
    pane.append(narr);

    // 2) 문장 ↔ 액션 동기화 보드
    const sync = el("section", { class: "block" });
    pane.append(sync);
    const renderSync = () => { sync.innerHTML = ""; sync.append(syncBoard(seg, (idx) => focusCard(idx))); };

    // 3) 액션 카드
    const addSel = el("select", { class: "add-action" });
    addSel.append(el("option", { value: "" }, "+ 액션 추가…"));
    let lastCat = null;
    for (const a of state.catalog) {
      if (a.category !== lastCat) { lastCat = a.category; addSel.append(el("optgroup", { label: a.category })); }
      addSel.lastChild.append(el("option", { value: a.name }, `${actIcon(a.name)} ${actLabel(a.name)} (${a.name}) — ${a.doc}`.slice(0, 80)));
    }
    addSel.addEventListener("change", () => {
      if (!addSel.value) return;
      const t = state.catalogByName[addSel.value];
      const act = { do: addSel.value, ...(JSON.parse(JSON.stringify(t.template || {}))) };
      seg.actions.push(act); state.expanded.add(act);
      touched(); renderSegEditor(); renderSegList();
      setTimeout(() => focusCard(seg.actions.length - 1), 0);
    });
    const cardsBox = el("div", { class: "cards" });
    const acts = el("section", { class: "block" },
      el("div", { class: "block-head" }, el("h3", {}, `③ 액션 ${seg.actions.length}개`),
        el("span", { class: "hint" }, "위에서 아래 순서로 실행 · 카드를 누르면 세부 설정"), el("span", { class: "spacer" }),
        el("button", { class: "ghost mini", onclick: () => { seg.actions.forEach((a) => state.expanded.add(a)); renderCards(); } }, "모두 펼치기"),
        el("button", { class: "ghost mini", onclick: () => { state.expanded.clear(); renderCards(); } }, "모두 접기"),
        addSel),
      cardsBox);
    pane.append(acts);
    const renderCards = () => { cardsBox.innerHTML = ""; seg.actions.forEach((act, i) => cardsBox.append(actionCard(seg, act, i))); };
    function focusCard(idx) {
      const act = seg.actions[idx]; if (!act) return;
      state.expanded.add(act); renderCards();
      const c = cardsBox.children[idx]; if (!c) return;
      c.scrollIntoView({ behavior: "smooth", block: "center" });
      c.classList.add("flash"); setTimeout(() => c.classList.remove("flash"), 1200);
    }
    renderSync(); renderCards();
  }

  /** 문장(줄) ↔ 액션(칩) 표 + 비율 시간 바. 액션은 at 에 따라 해당 문장 줄에, at 이 없으면 앞 액션과 같은 줄에 놓인다. */
  function syncBoard(seg, onPick) {
    const info = sentencesFor(seg);
    const sents = info.list;
    const total = info.exact && sents.length ? sents[sents.length - 1].end : null;
    const rows = sents.map((s) => ({ s, acts: [] }));
    const before = { s: null, acts: [] }, numeric = [];   // 문장 없이 시작하는 것 / 초 단위 at
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
    box.append(el("div", { class: "block-head" }, el("h3", {}, "② 문장 ↔ 액션 동기화"),
      el("span", { class: "s-mode " + (info.exact ? "exact" : "guess"),
        title: info.exact ? "TTS 엔진이 실제로 끊어 읽은 문장 경계와 시각입니다 (at: sN 의 기준)" : "문장부호로 추정한 경계입니다. 숫자 뒤의 '.' 등은 TTS 가 다르게 끊을 수 있으니 ▶ 듣기로 확인하세요" },
        info.exact ? "실제 경계 · 시각" : "추정 경계"),
      el("span", { class: "hint" }, "줄 = 한 문장, 칩 = 그 문장이 시작될 때 실행되는 액션. 칩을 누르면 카드로 이동")));

    if (total) {
      const bar = el("div", { class: "timebar" });
      sents.forEach((s) => bar.append(el("span", { class: "blk", style: `left:${(s.start / total) * 100}%;width:${((s.end - s.start) / total) * 100}%`, title: `s${s.i} ${s.start.toFixed(1)}–${s.end.toFixed(1)}s` }, `s${s.i}`)));
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
    const chip = ({ a, i, warn }) => el("button", { class: "achip" + (warn ? " warn" : ""), style: `--c:${actColor(a.do)}`, title: `${i + 1}. ${a.do} — ${summarize(a)}`, onclick: () => onPick(i) },
      el("b", {}, actIcon(a.do)), el("span", { class: "nm" }, actLabel(a.do)), el("span", { class: "sm" }, short(summarize(a), 26)),
      a.at === undefined || a.at === null || a.at === "" ? null : el("span", { class: "at" }, atText(a.at)));
    const row = (label, sub, actsList, extraCls = "") => el("div", { class: "srow " + extraCls },
      el("div", { class: "sent" }, el("b", {}, label), sub ? el("span", { class: "t" }, sub) : null),
      el("div", { class: "chips" }, ...(actsList.length ? actsList.map(chip) : [el("span", { class: "none" }, "—")])));
    if (before.acts.length) table.append(row("시작", "", before.acts, "pre"));
    rows.forEach(({ s, acts }) => {
      const label = el("span", { class: "sn", title: "클릭하면 at 값(sN)을 복사", onclick: () => { navigator.clipboard?.writeText("s" + s.i); toast(`s${s.i} 복사됨 — 액션의 at 칸에 붙이세요`); } }, `s${s.i}`);
      const r = el("div", { class: "srow" },
        el("div", { class: "sent" }, label, s.start !== undefined ? el("span", { class: "t" }, `${s.start.toFixed(1)}s`) : null, el("span", { class: "txt", title: s.text }, s.text)),
        el("div", { class: "chips" }, ...(acts.length ? acts.map(chip) : [el("span", { class: "none" }, "—")])));
      table.append(r);
    });
    numeric.sort((x, y) => x.t - y.t).forEach((r) => table.append(row(`${r.t}s`, "", r.acts, "num")));
    if (!rows.length && !before.acts.length) table.append(el("p", { class: "hint" }, "내레이션을 쓰면 문장별 줄이 생깁니다."));
    box.append(table);
    return box;
  }

  function field(label, control) { return el("div", { class: "field" }, el("label", {}, label), control); }
  function inp(value, onchange, attrs = {}) {
    const i = el("input", { type: "text", value: value ?? "", ...attrs });
    i.addEventListener("change", () => onchange(i.value));
    return i;
  }
  function moveSeg(d) {
    const i = state.sel, j = i + d;
    if (j < 0 || j >= state.doc.segments.length) return;
    const s = state.doc.segments; [s[i], s[j]] = [s[j], s[i]]; state.sel = j; touched(); renderSegList(); renderSegEditor();
  }
  function dupSeg() {
    const s = JSON.parse(JSON.stringify(state.doc.segments[state.sel])); s.id = (s.id || "seg") + "_copy";
    state.doc.segments.splice(state.sel + 1, 0, s); state.sel += 1; touched(); renderSegList(); renderSegEditor();
  }
  function delSeg() {
    if (!confirm("이 세그먼트를 삭제할까요?")) return;
    state.doc.segments.splice(state.sel, 1); state.sel = Math.max(0, state.sel - 1); touched(); renderSegList(); renderSegEditor();
  }

  // ------------------------------------------------------------------ 액션 카드 (접힘: 아이콘·이름·요약·시각 / 펼침: 세부 설정)
  function actionCard(seg, act, i) {
    const spec = state.catalogByName[act.do];
    const color = actColor(act.do);
    const open = state.expanded.has(act);
    const card = el("div", { class: "card" + (open ? " open" : ""), style: `--c:${color}` });
    const nSent = sentencesFor(seg).list.length;
    const atWarn = typeof act.at === "string" && /^s\d+$/.test(act.at) && Number(act.at.slice(1)) > Math.max(1, nSent);
    if (atWarn) card.classList.add("at-warn");

    // 접힌 머리
    const rerenderCard = () => { const n = actionCard(seg, act, i); card.replaceWith(n); };
    const head = el("div", { class: "head", onclick: (e) => { if (e.target.closest("button, input, select")) return; open ? state.expanded.delete(act) : state.expanded.add(act); rerenderCard(); } },
      el("span", { class: "idx" }, String(i + 1)),
      el("span", { class: "ico" }, actIcon(act.do)),
      el("span", { class: "name" }, actLabel(act.do), el("code", {}, act.do)),
      el("span", { class: "sum", title: summarize(act) }, summarize(act) || el("i", { class: "hint" }, spec ? spec.doc : "알 수 없는 액션")),
      el("span", { class: "timing" + (atWarn ? " warn" : "") + (act.at === undefined ? " seq" : ""), title: atWarn ? `문장이 ${nSent}개뿐입니다` : "실행 시각" },
        act.at === undefined || act.at === null || act.at === "" ? "이어서" : `▶ ${atText(act.at)}`),
      act.run_time !== undefined ? el("span", { class: "rt", title: "run_time(초)" }, `${act.run_time}s`) : null,
      el("span", { class: "tools" },
        el("button", { class: "ghost mini", title: "위로", onclick: () => swapAct(seg, i, -1) }, "↑"),
        el("button", { class: "ghost mini", title: "아래로", onclick: () => swapAct(seg, i, 1) }, "↓"),
        el("button", { class: "ghost mini", title: "복제", onclick: () => { seg.actions.splice(i + 1, 0, JSON.parse(JSON.stringify(act))); touched(); renderSegEditor(); renderSegList(); } }, "⧉"),
        el("button", { class: "ghost mini", title: "삭제", onclick: () => { if (confirm(`${actLabel(act.do)} 액션을 삭제할까요?`)) { seg.actions.splice(i, 1); touched(); renderSegEditor(); renderSegList(); } } }, "✕")),
      el("span", { class: "chev" }, open ? "▾" : "▸"));
    card.append(head);
    if (!open) return card;

    // ---- 펼친 본문
    const body = el("div", { class: "body" });

    // 종류 / 시각 / 길이
    const doSel = el("select", { class: "do" });
    let lastCat = null;
    for (const a of state.catalog) {
      if (a.category !== lastCat) { lastCat = a.category; doSel.append(el("optgroup", { label: a.category })); }
      doSel.lastChild.append(el("option", { value: a.name }, `${actIcon(a.name)} ${actLabel(a.name)} (${a.name})`));
    }
    if (!spec) doSel.append(el("option", { value: act.do }, act.do + " (?)"));
    doSel.value = act.do;
    doSel.addEventListener("change", () => { act.do = doSel.value; touched(); renderSegEditor(); });
    const atIn = el("input", { class: "at", value: act.at ?? "", placeholder: "예: s2 / 3.5", title: "실행 시각: sN(문장 N 시작) 또는 초. 비우면 앞 액션이 끝난 뒤 이어서" });
    atIn.addEventListener("change", () => { const v = parseVal(atIn.value); if (v === undefined) delete act.at; else act.at = v; touched(); renderSegEditor(); });
    const rtIn = el("input", { class: "rt", value: act.run_time ?? "", placeholder: "기본", title: "애니메이션 길이(초)" });
    rtIn.addEventListener("change", () => { const v = parseVal(rtIn.value); if (v === undefined) delete act.run_time; else act.run_time = v; touched(); rerenderCard(); });
    const sents = sentencesFor(seg).list;
    const atPick = el("select", { class: "atpick", title: "문장을 골라 at 을 정합니다" });
    atPick.append(el("option", { value: "" }, "문장 선택…"));
    atPick.append(el("option", { value: "__seq" }, "이어서 (at 없음)"));
    sents.forEach((s) => atPick.append(el("option", { value: "s" + s.i }, `s${s.i}${s.start !== undefined ? ` (${s.start.toFixed(1)}s)` : ""} ${short(s.text, 28)}`)));
    atPick.addEventListener("change", () => { if (!atPick.value) return; if (atPick.value === "__seq") delete act.at; else act.at = atPick.value; touched(); renderSegEditor(); });
    body.append(el("div", { class: "ctl" },
      el("span", { class: "ctl-item" }, el("label", {}, "종류"), doSel),
      el("span", { class: "ctl-item" }, el("label", {}, "시각(at)"), atIn, atPick),
      el("span", { class: "ctl-item" }, el("label", {}, "길이(run)"), rtIn, el("label", {}, "초"))));
    if (spec?.doc_full) body.append(el("p", { class: "doc" }, spec.doc_full));

    // 파라미터: 설정된 것만 표로, 나머지는 "+ 파라미터" 로 추가
    const params = el("div", { class: "params" });
    const skip = new Set(["do", "at", "run_time", "steps", "parts"]);
    const stepKeys = ["why", "from", "focus", "new", "cancel", "box", "pulse", "hold", "cancel_at", "underline", "same_line", "space"];
    const known = (spec?.params || []).map((p) => p.name).filter((n) => !skip.has(n));
    const setKeys = Object.keys(act).filter((k) => !skip.has(k) && !(act.do === "step" && stepKeys.includes(k)));
    const unset = known.filter((k) => !(k in act) && !(act.do === "step" && stepKeys.includes(k)));
    const required = (spec?.params || []).filter((p) => p.required && !skip.has(p.name)).map((p) => p.name);
    for (const k of [...required.filter((k) => !setKeys.includes(k)), ...setKeys]) {
      const pspec = (spec?.params || []).find((p) => p.name === k);
      const val = act[k];
      const long = typeof val === "string" && val.length > 60 || Array.isArray(val) && val.some((x) => typeof x === "string" && x.length > 30);
      const input = long ? el("textarea", { rows: Math.min(6, 1 + Math.ceil(fmtVal(val).length / 70)), spellcheck: "false" }) : el("input", { spellcheck: "false" });
      input.value = val === undefined ? "" : fmtVal(val);
      input.placeholder = pspec && pspec.default !== null && pspec.default !== undefined ? `기본 ${fmtVal(pspec.default)}` : (pspec?.required ? "필수" : "");
      if (val !== undefined && typeof val !== "string") input.classList.add("json");
      input.addEventListener("change", () => {
        const v = parseVal(input.value);
        if (v === undefined) delete act[k]; else act[k] = v;
        touched(); rerenderCard();
      });
      if (k === "fn" && act.do === "custom" && state.hooks.length) input.setAttribute("list", "hooksList");
      if (k === "section" && act.do === "goto") input.setAttribute("list", "sectionsList");
      if (k === "color") input.setAttribute("list", "colorsList");
      params.append(el("span", { class: "k" + (pspec?.required ? " req" : "") + (pspec ? "" : " extra"), title: pspec ? `${pspec.type || ""}${pspec.required ? " · 필수" : ""}` : "카탈로그에 없는 항목" }, k), input,
        el("span", { class: "x", title: "이 항목 지우기", onclick: () => { delete act[k]; touched(); rerenderCard(); } }, "✕"));
    }
    body.append(params);
    ensureDatalists();

    // + 파라미터
    const addP = el("select", { class: "addp" });
    addP.append(el("option", { value: "" }, unset.length ? `+ 파라미터 (${unset.length}개 더)…` : "+ 파라미터…"));
    for (const k of unset) { const p = (spec?.params || []).find((q) => q.name === k); addP.append(el("option", { value: k }, `${k}${p && p.default !== null && p.default !== undefined ? ` — 기본 ${fmtVal(p.default)}` : ""}`)); }
    addP.append(el("option", { value: "__custom" }, "직접 입력…"));
    addP.addEventListener("change", () => {
      let k = addP.value; if (!k) return;
      if (k === "__custom") { k = prompt("추가할 항목 이름"); if (!k) return; }
      const p = (spec?.params || []).find((q) => q.name === k);
      act[k] = p && p.default !== null && p.default !== undefined ? JSON.parse(JSON.stringify(p.default)) : "";
      touched(); rerenderCard();
    });
    const rawBtn = el("button", { class: "ghost mini", onclick: () => { state.rawOpen.has(act) ? state.rawOpen.delete(act) : state.rawOpen.add(act); rerenderCard(); } }, state.rawOpen.has(act) ? "JSON 닫기" : "JSON 으로 보기");
    body.append(el("div", { class: "foot" }, addP, el("span", { class: "hint" }, "값: 숫자/true/false/[목록]/{매핑} 자동 인식"), el("span", { class: "spacer" }), rawBtn));

    // derive/step 전용: 단계 편집기
    if (act.do === "derive") body.append(stepsEditor(act.steps = act.steps || [], () => { touched(); }, false, sents));
    if (act.do === "step") body.append(stepsEditor([act], () => { touched(); }, true, sents));

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

  function swapAct(seg, i, d) {
    const j = i + d; if (j < 0 || j >= seg.actions.length) return;
    [seg.actions[i], seg.actions[j]] = [seg.actions[j], seg.actions[i]]; touched(); renderSegEditor();
  }

  const COLOR_NAMES = ["exp", "log", "q1", "q2", "point", "rect", "axis_sym", "guide", "ok", "warn", "chalk", "accent", "highlight", "muted", "text"];
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

  /** derive.steps 또는 step 액션 하나를 편집하는 표. single=true 면 steps 배열 대신 액션 자체가 한 단계.
   *  각 단계: [번호] 조각 미리보기(칩) · 조각 입력 · 이유 · 옵션(접힘) */
  function stepsEditor(steps, onchange, single = false, sents = []) {
    const box = el("div", { class: "steps" });
    const optOpen = new Set();
    const render = () => {
      box.innerHTML = "";
      box.append(el("div", { class: "block-head" }, el("h4", {}, single ? "이 단계의 식" : `전개 단계 ${steps.length}개`),
        el("span", { class: "hint" }, "조각은 \" | \" 로 구분 — 이전 줄과 같은 조각은 미끄러지고, 바뀐 조각만 강조되어 날아옵니다"),
        el("span", { class: "spacer" }),
        single ? null : el("button", { class: "ghost mini", onclick: () => { steps.push({ parts: ["=", ""] }); onchange(); render(); } }, "+ 단계")));
      steps.forEach((st, k) => {
        const parts = st.parts || (st.tex ? [st.tex] : []);
        const preview = el("div", { class: "preview" });
        parts.forEach((p) => preview.append(el("span", { class: "pc" + (p === "=" || /^[+\-−×·,]$/.test(p) || /^\\(times|cdot|pm|Rightarrow)$/.test(p) ? " op" : "") }, stripTex(p) || " ")));
        if (st.why) preview.append(el("span", { class: "why" }, `(∵ ${stripTex(st.why)})`));
        const flags = [st.box ? "상자" : "", st.pulse ? "펄스" : "", st.cancel ? "소거" : "", st.from ? "대입" : "", st.at ? `▶ ${atText(st.at)}` : "", st.hold ? `hold ${st.hold}` : ""].filter(Boolean);
        flags.forEach((f) => preview.append(el("span", { class: "flag" }, f)));

        const partsIn = el("input", { value: joinParts(parts), placeholder: "조각 | 조각 | …  (예: = | 2^{3} | \\times | x)", spellcheck: "false" });
        partsIn.addEventListener("change", () => { st.parts = splitParts(partsIn.value); delete st.tex; onchange(); render(); });
        const whyIn = el("input", { value: st.why || "", placeholder: "(∵ 이유) — 한글+수식", spellcheck: "false" });
        whyIn.addEventListener("change", () => { if (whyIn.value.trim()) st.why = whyIn.value; else delete st.why; onchange(); render(); });
        const optBtn = el("button", { class: "ghost mini", onclick: () => { optOpen.has(st) ? optOpen.delete(st) : optOpen.add(st); render(); } }, optOpen.has(st) ? "옵션 ▾" : "옵션 ▸");
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
          const atSel = el("select", { class: "small" }); atSel.append(el("option", { value: "" }, "문장…")); sents.forEach((s) => atSel.append(el("option", { value: "s" + s.i }, `s${s.i}`)));
          atSel.addEventListener("change", () => { if (atSel.value) { st.at = atSel.value; onchange(); render(); } });
          opts.append(
            el("div", { class: "grp" }, el("b", {}, "시각"), txt("at", "at", "small", "s2", "이 단계를 시작할 문장/초"), atSel, txt("hold", "hold", "small", "s3", "출처 상자만 먼저 짚어 두고 이 문장부터 움직임"), txt("run_time", "run", "small", "2.0", "단계 애니메이션 길이(초)")),
            el("div", { class: "grp" }, el("b", {}, "강조"), chk("box", "상자", "결과에 분필 상자"), chk("pulse", "펄스", "상자를 한 번 두드림"), chk("underline", "밑줄", "")),
            el("div", { class: "grp" }, el("b", {}, "매칭"), txt("from", "from", "wide", '{"2^{2}": "x^{2}"}', "대입: 새 조각 ← 이전 조각"), txt("focus", "focus", "wide", '["2\\\\cdot3x^{2}"]', "출처를 이 조각들로 한정"), txt("new", "new", "wide", '["6", "x^{2}"]', "완전히 새로 쓰는 조각")),
            el("div", { class: "grp" }, el("b", {}, "소거"), txt("cancel", "cancel", "wide", '["a_7", 5]', "취소선을 그을 조각(문자열/인덱스)"), txt("cancel_at", "cancel_at", "small", "s5", "취소선을 긋는 문장")),
          );
          row.append(opts);
        }
        box.append(row);
      });
    };
    render();
    return box;
  }

  // ------------------------------------------------------------------ 설정 탭
  function renderSettings() {
    const pane = $("#settingsEditor");
    pane.innerHTML = "";
    const doc = state.doc;
    doc.meta = doc.meta || {}; doc.layout = doc.layout || {}; doc.layout.chalk = doc.layout.chalk || {}; doc.params = doc.params || {};
    const m = doc.meta, ch = doc.layout.chalk;
    const set = (obj, key, cast = (v) => v) => (v) => { const x = cast(v); if (x === undefined || x === "") delete obj[key]; else obj[key] = x; touched(); if (obj === m && key === "title") loadProjects(); };
    const num = (v) => (v === "" ? undefined : Number(v));
    const sel = (value, options, onchange) => { const s = el("select", {}); for (const o of options) s.append(el("option", { value: o }, o)); s.value = value; s.addEventListener("change", () => onchange(s.value)); return s; };

    const wrap = el("div", { class: "settings" });
    wrap.append(el("h2", {}, "메타"));
    const g = el("div", { class: "grid2" });
    g.append(field("제목", inp(m.title, set(m, "title"))), field("부제", inp(m.subtitle, set(m, "subtitle"))),
      field("목소리", sel(m.voice || "ko-KR-InJoonNeural", ["ko-KR-InJoonNeural", "ko-KR-SunHiNeural", "ko-KR-HyunsuMultilingualNeural"], set(m, "voice"))),
      field("속도", inp(m.rate || "+0%", set(m, "rate"), { placeholder: "+0%" })),
      field("해상도", sel(m.resolution || "1080p", ["480p", "720p", "1080p", "1440p", "2160p"], set(m, "resolution"))),
      field("fps", inp(m.fps ?? 30, set(m, "fps", num))),
      field("스타일", sel(m.style || "panel", ["chalkboard", "panel"], set(m, "style"))),
      field("자막", sel(m.subtitles || "burn", ["burn", "soft", "none"], set(m, "subtitles"))),
      field("세그먼트 여백", inp(m.segment_pad ?? 0.45, set(m, "segment_pad", num))));
    wrap.append(g);

    wrap.append(el("h2", {}, "칠판 배치 (chalkboard)"));
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
      secs.append(el("div", { class: "row" }, el("span", { class: "hint" }, "칸(section): goto 로 카메라가 이동하는 칠판 영역. layout=split 이면 왼쪽에 그래프, 오른쪽에 판서"),
        el("span", { class: "spacer" }), el("button", { class: "ghost mini", onclick: () => { ch.sections.push({ id: "sec" + (ch.sections.length + 1), title: "", layout: "full" }); touched(); renderSecs(); } }, "+ 칸")));
      ch.sections.forEach((s, i) => {
        secs.append(el("div", { class: "sec" },
          inp(s.id, (v) => { s.id = v; touched(); }, { placeholder: "id" }),
          inp(s.title || "", (v) => { s.title = v; touched(); }, { placeholder: "제목(판서)" }),
          sel(s.layout || "full", ["full", "split"], (v) => { s.layout = v; touched(); }),
          inp(s.graph_width ?? "", (v) => { const n = num(v); if (n === undefined) delete s.graph_width; else s.graph_width = n; touched(); }, { placeholder: "그림폭" }),
          el("span", {}, el("button", { class: "ghost mini", onclick: () => { if (i > 0) { [ch.sections[i - 1], ch.sections[i]] = [ch.sections[i], ch.sections[i - 1]]; touched(); renderSecs(); } } }, "↑"),
            el("button", { class: "ghost mini", onclick: () => { ch.sections.splice(i, 1); touched(); renderSecs(); } }, "✕"))));
      });
    };
    renderSecs();
    wrap.append(secs);

    wrap.append(el("h2", {}, "params (수식에서 쓰는 상수)"));
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
      state.yamlText = r.yaml; state.doc = r.doc; state.yamlDirty = false; setDirty(false);
      if (r.sentences) setSentences(r.sentences, r.doc);
      showCheck(r.check);
      toast(r.check.ok ? "저장됨" : `저장됨 — 오류 ${r.check.errors.length}개 (검사 결과 탭)`, r.check.ok ? "ok" : "bad");
      if (!r.check.ok) switchTab("check");
      renderSegList(); renderSegEditor();
      $("#yamlText").value = state.yamlText;
      loadProjects();
    } catch (e) { toast("저장 실패: " + e.message, "bad"); }
  }

  async function validate(tex) {
    if (!state.pid) return;
    const btn = tex ? $("#btnTex") : $("#btnValidate");
    btn.disabled = true;
    try {
      const body = state.yamlDirty ? { yaml: $("#yamlText").value, tex } : { doc: state.doc, tex };
      const r = await api(`/api/projects/${state.pid}/validate`, { method: "POST", body });
      showCheck(r); switchTab("check");
      toast(r.ok ? (tex ? "LaTeX 포함 검사 통과" : "검사 통과") : `오류 ${r.errors.length}개`, r.ok ? "ok" : "bad");
    } catch (e) { toast(e.message, "bad"); }
    btn.disabled = false;
  }

  function showCheck(r) {
    const box = $("#checkBox");
    box.innerHTML = "";
    box.append(el("div", { class: "item" }, r.ok ? "✅ 통과" : `❌ 오류 ${r.errors.length}개`, r.summary?.segments !== undefined ? ` — 세그먼트 ${r.summary.segments}개, 액션 ${r.summary.actions}개` : ""));
    for (const e of r.errors || []) box.append(el("div", { class: "item err" }, "✗ ", el("code", {}, e.where), " ", e.msg));
    for (const w of r.warnings || []) box.append(el("div", { class: "item warn" }, "△ ", el("code", {}, w.where), " ", w.msg));
  }

  // ------------------------------------------------------------------ 렌더 작업
  async function startBuild(kind) {
    if (!state.pid) return;
    if (state.dirty) { await save(); if (state.dirty) return; }
    const body = { preview: kind !== "final" };
    if (kind === "partial") {
      const seg = state.doc.segments[state.sel];
      if (!seg) return;
      body.segments = [seg.id];
    }
    try {
      const job = await api(`/api/projects/${state.pid}/build`, { method: "POST", body });
      $("#logBox").textContent = ""; state.logOffset = 0;
      attachJob(job); switchTab("log");
      toast(kind === "partial" ? `세그먼트 '${body.segments[0]}' 렌더 시작` : kind === "final" ? "최종 렌더 시작" : "프리뷰 렌더 시작");
    } catch (e) { toast(e.message, "bad"); }
  }

  function attachJob(job) {
    state.job = job; state.logOffset = 0; $("#logBox").textContent = "";
    updateJobStatus(job);
    clearInterval(state.pollTimer);
    state.pollTimer = setInterval(pollJob, 1500);
    pollJob();
  }

  async function pollJob() {
    if (!state.job) return;
    try {
      const r = await api(`/api/jobs/${state.job.id}?offset=${state.logOffset}`);
      if (r.log) { const lb = $("#logBox"); lb.textContent += r.log; lb.scrollTop = lb.scrollHeight; state.logOffset = r.offset; }
      state.job = r.job; updateJobStatus(r.job);
      if (r.job.status !== "running") {
        clearInterval(state.pollTimer); state.pollTimer = null;
        const outs = await api(`/api/projects/${state.pid}/outputs`);
        state.outputs = outs; renderOutputs();
        if (r.job.status === "done") { toast("렌더 완료 ✓", "ok"); switchTab(r.job.kind === "final" ? "verify" : "video"); }
        else if (r.job.status === "failed") { toast("렌더 실패 — 로그를 확인하세요", "bad"); switchTab("log"); }
        loadProjects();
      }
    } catch (e) { clearInterval(state.pollTimer); toast(e.message, "bad"); }
  }

  function updateJobStatus(job) {
    const s = $("#jobStatus");
    const running = job && job.status === "running";
    $("#btnCancel").classList.toggle("hidden", !running);
    for (const id of ["btnPartial", "btnPreview", "btnFinal"]) $("#" + id).disabled = !!running;
    if (!job) { s.textContent = ""; s.className = "status"; return; }
    const label = { preview: "프리뷰", final: "최종", partial: "부분" }[job.kind] || job.kind;
    s.className = "status " + job.status;
    s.textContent = running ? `⏳ ${label} 렌더 중… (${job.started.slice(11, 19)} 시작)` : job.status === "done" ? `✓ ${label} 렌더 완료` : job.status === "failed" ? `✗ ${label} 렌더 실패 (code ${job.returncode})` : "중지됨";
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
    if (full.preview) opts.push(["preview", "프리뷰(480p)", full.preview]);
    if (part.preview) opts.push(["partial", "부분 렌더(선택 세그먼트)", part.preview]);
    if (part.final) opts.push(["partial_final", "부분 렌더(최종 해상도)", part.final]);
    for (const [k, label, url] of opts) vs.append(el("option", { value: k, "data-url": url }, label));
    const video = $("#video");
    if (opts.length) {
      vs.value = opts.some((x) => x[0] === prev) ? prev : opts[0][0];
      const url = vs.selectedOptions[0].dataset.url;
      if (video.getAttribute("src") !== url) video.src = url;
      $("#videoInfo").textContent = "";
    } else { video.removeAttribute("src"); $("#videoInfo").textContent = "아직 렌더된 영상이 없습니다. 프리뷰 렌더를 눌러 보세요."; }
    vs.onchange = () => { video.src = vs.selectedOptions[0].dataset.url; };

    const chips = $("#segChips"); chips.innerHTML = "";
    const tl = (vs.value?.startsWith("partial") ? part.timeline : full.timeline) || {};
    for (const s of tl.segments || []) {
      chips.append(el("span", { class: "chip", onclick: () => { video.currentTime = s.start; video.play().catch(() => {}); } }, s.id, el("small", {}, `${s.start.toFixed(1)}s`)));
    }
    const sb = $("#storyboard");
    if (full.storyboard) { sb.src = full.storyboard; sb.classList.remove("hidden"); $("#storyboardHint").textContent = ""; }
    else { sb.removeAttribute("src"); $("#storyboardHint").textContent = "프리뷰/최종 렌더 뒤에 세그먼트별 대표 프레임이 여기에 표시됩니다."; }

    const vb = $("#verifyBox"); vb.innerHTML = "";
    const rep = full.verify_report;
    if (rep) {
      const okN = rep.checks.filter((c) => c.ok).length;
      vb.append(el("div", { class: "sum" }, `${rep.ok ? "✅" : "❌"} ${okN} / ${rep.checks.length} 통과 — ${rep.video}`));
      const t = el("table");
      for (const c of rep.checks) t.append(el("tr", {}, el("td", { class: c.ok ? "ok" : "bad" }, c.ok ? "PASS" : "FAIL"), el("td", {}, c.name), el("td", { class: "hint" }, c.detail || "")));
      vb.append(t);
    } else vb.append(el("p", { class: "hint" }, "렌더 뒤 21항목 자동 검증 결과가 표시됩니다."));
  }

  // ------------------------------------------------------------------ 타임라인
  async function loadTiming() {
    const btn = $("#btnTiming"); btn.disabled = true; btn.textContent = "TTS 합성 중…";
    try { state.timing = await api(`/api/projects/${state.pid}/timing`); renderTimeline(); }
    catch (e) { toast(e.message, "bad"); }
    btn.disabled = false; btn.textContent = "문장 타이밍 불러오기 (TTS)";
  }
  function renderTimeline() {
    const box = $("#timelineBox"); box.innerHTML = "";
    const t = state.timing;
    if (!t) { box.append(el("p", { class: "hint" }, "내레이션을 합성해 세그먼트/문장 길이를 봅니다 (캐시되어 두 번째부터는 즉시).")); return; }
    const total = t.total || 1;
    box.append(el("p", { class: "hint" }, `총 예상 길이 ≈ ${t.total.toFixed(1)}s (${(t.total / 60).toFixed(1)}분) — 액션이 내레이션보다 길면 실제 영상은 더 길어집니다`));
    t.segments.forEach((s, i) => {
      const dur = s.end - s.start;
      const bar = el("div", { class: "bar" + (i === state.sel ? " on" : ""), style: `width:${Math.max(18, (dur / total) * 100)}%`,
        onclick: () => { state.sel = i; showPane("seg"); renderSegList(); renderSegEditor(); renderTimeline(); } },
        el("span", { class: "lab" }, s.id), el("span", { class: "dur" }, `${dur.toFixed(1)}s`));
      for (const sn of s.sentences) {
        bar.append(el("span", { class: "tick", style: `left:${(sn.start / Math.max(dur, 0.1)) * 100}%`, title: `s${sn.i} (${sn.start.toFixed(1)}s) ${sn.text}`,
          onclick: (e) => { e.stopPropagation(); navigator.clipboard?.writeText("s" + sn.i); toast(`s${sn.i} 복사됨 — 액션의 at 칸에 붙이세요`); } }, "s" + sn.i));
      }
      box.append(bar);
    });
  }

  // ------------------------------------------------------------------ 탭/모달/이력
  function switchTab(name) {
    $$("#preview .tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
    $$("#preview .tab").forEach((t) => t.classList.toggle("on", t.id === "tab-" + name));
  }
  function modal(content) {
    const m = $("#modal"); $("#modalBody").innerHTML = ""; $("#modalBody").append(content); m.classList.remove("hidden");
    m.onclick = (e) => { if (e.target === m) m.classList.add("hidden"); };
  }
  const closeModal = () => $("#modal").classList.add("hidden");

  async function showHistory() {
    const items = await api(`/api/projects/${state.pid}/history`);
    const ul = el("ul");
    if (!items.length) ul.append(el("li", {}, "저장 이력이 없습니다."));
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
    const idIn = el("input", { placeholder: "영문 id (예: 2026_suneung_q22)", style: "width:100%" });
    const titleIn = el("input", { placeholder: "제목 (예: 2026학년도 수능 수학 22번)", style: "width:100%;margin-top:8px" });
    const btn = el("button", { class: "accent", style: "margin-top:12px", onclick: async () => {
      try {
        await api("/api/projects", { method: "POST", body: { id: idIn.value.trim(), title: titleIn.value.trim() || "새 영상" } });
        closeModal(); await loadProjects(); await openProject(idIn.value.trim()); toast("프로젝트를 만들었습니다 — 템플릿 시나리오가 들어 있습니다", "ok");
      } catch (e) { toast(e.message, "bad"); }
    } }, "만들기");
    modal(el("div", {}, el("h3", {}, "새 프로젝트"), idIn, titleIn, el("p", { class: "hint" }, "projects/<id>/project.yaml 이 칠판 스타일 템플릿으로 만들어집니다. 커스텀 애니메이션은 같은 폴더의 hooks.py 에 함수로 추가하면 custom 액션에서 쓸 수 있습니다."), btn));
    idIn.focus();
  }

  // ------------------------------------------------------------------ 이벤트
  function bind() {
    $("#projectSelect").addEventListener("change", (e) => openProject(e.target.value));
    $("#btnNew").addEventListener("click", newProjectDialog);
    $("#btnSave").addEventListener("click", save);
    $("#btnValidate").addEventListener("click", () => validate(false));
    $("#btnTex").addEventListener("click", () => validate(true));
    $("#btnPartial").addEventListener("click", () => startBuild("partial"));
    $("#btnPreview").addEventListener("click", () => startBuild("preview"));
    $("#btnFinal").addEventListener("click", () => startBuild("final"));
    $("#btnCancel").addEventListener("click", async () => { if (state.job) { await api(`/api/jobs/${state.job.id}/cancel`, { method: "POST" }); toast("중지 요청"); } });
    $("#btnAddSeg").addEventListener("click", () => {
      state.doc.segments.push({ id: "seg" + (state.doc.segments.length + 1), narration: "", actions: [] });
      state.sel = state.doc.segments.length - 1; touched(); showPane("seg"); renderSegList(); renderSegEditor();
    });
    $("#tabSettings").addEventListener("click", () => showPane("settings"));
    $("#tabYaml").addEventListener("click", () => showPane("yaml"));
    $("#btnHistory").addEventListener("click", showHistory);
    $("#yamlText").addEventListener("input", () => { state.yamlDirty = true; setDirty(true); });
    $("#btnYamlApply").addEventListener("click", async () => {
      try {
        const r = await api("/api/yaml/parse", { method: "POST", body: { yaml: $("#yamlText").value } });
        state.doc = r.doc; state.yamlText = $("#yamlText").value; state.sel = Math.min(state.sel, Math.max(0, (state.doc.segments || []).length - 1));
        renderSegList(); renderSegEditor(); renderSettings(); showPane("seg"); toast("YAML 을 폼에 반영했습니다 (저장은 별도)", "ok");
      } catch (e) { toast(e.message, "bad"); }
    });
    $$("#preview .tabs button").forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));
    $("#btnTiming").addEventListener("click", loadTiming);
    document.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); } });
    window.addEventListener("beforeunload", (e) => { if (state.dirty) { e.preventDefault(); e.returnValue = ""; } });
  }

  // ------------------------------------------------------------------ 시작
  async function init() {
    bind();
    state.catalog = await api("/api/actions");
    state.catalogByName = Object.fromEntries(state.catalog.map((a) => [a.name, a]));
    await loadProjects();
    const want = location.hash.slice(1);
    const first = state.projects.find((p) => p.id === want) || state.projects[0];
    if (first) await openProject(first.id);
    else { $("#segEditor").append(el("p", { class: "hint" }, "프로젝트가 없습니다. 상단의 '+ 새 프로젝트'로 시작하세요.")); }
  }
  init().catch((e) => toast("초기화 실패: " + e.message, "bad"));
})();
