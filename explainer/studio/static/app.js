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
    state.rawOpen.clear();
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

  // ------------------------------------------------------------------ 세그먼트 목록
  function renderSegList() {
    const ul = $("#segList");
    ul.innerHTML = "";
    state.doc.segments.forEach((seg, i) => {
      const li = el("li", { class: i === state.sel ? "on" : "", draggable: "true",
        onclick: () => { state.sel = i; showPane("seg"); renderSegList(); renderSegEditor(); } },
        el("span", { class: "n" }, String(i + 1)),
        el("span", { class: "id" }, seg.id || "(id 없음)"),
        el("span", { class: "cnt" }, `${(seg.actions || []).length}개`));
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
    const head = el("div", { class: "row" },
      el("h2", {}, `세그먼트 ${state.sel + 1} / ${state.doc.segments.length}`),
      el("span", { class: "spacer" }),
      el("button", { class: "ghost mini", title: "위로", onclick: () => moveSeg(-1) }, "↑"),
      el("button", { class: "ghost mini", title: "아래로", onclick: () => moveSeg(1) }, "↓"),
      el("button", { class: "ghost mini", onclick: () => dupSeg() }, "복제"),
      el("button", { class: "danger mini", onclick: () => delSeg() }, "삭제"));
    pane.append(head);

    pane.append(field("id", inp(seg.id || "", (v) => { seg.id = v; touched(); renderSegList(); }, { placeholder: "예: read_problem" })));
    pane.append(field("여백 pad(s)", inp(seg.pad ?? "", (v) => { const n = parseVal(v); if (n === undefined) delete seg.pad; else seg.pad = n; touched(); }, { placeholder: "기본 meta.segment_pad" })));

    // 내레이션
    const narr = el("div", { class: "narr" });
    const ta = el("textarea", { placeholder: "내레이션. 문장(., ?, !)으로 끊으면 at: s2 처럼 문장 시작에 애니메이션을 맞출 수 있습니다." });
    ta.value = seg.narration || "";
    const sentBox = el("div", { class: "sentences" });
    const renderSent = (timed) => {
      sentBox.innerHTML = "";
      const sents = timed || splitSentences(ta.value).map((t, i) => ({ i: i + 1, text: t }));
      for (const s of sents) {
        sentBox.append(el("span", { class: "s", title: "클릭하면 at 값(sN)을 복사", onclick: () => { navigator.clipboard?.writeText("s" + s.i); toast(`s${s.i} 복사됨`); } },
          el("b", {}, "s" + s.i), s.text.length > 46 ? s.text.slice(0, 46) + "…" : s.text,
          s.start !== undefined ? el("span", { class: "t" }, `${s.start.toFixed(1)}s`) : null));
      }
    };
    ta.addEventListener("input", () => { seg.narration = ta.value; touched(); renderSent(); });
    const audio = el("audio", { controls: "", class: "hidden", style: "height:28px" });
    const btnTts = el("button", { class: "ghost mini", onclick: async () => {
      btnTts.disabled = true; btnTts.textContent = "합성 중…";
      try {
        const r = await api("/api/tts", { method: "POST", body: { text: ta.value, voice: seg.voice || state.doc.meta.voice || "ko-KR-InJoonNeural", rate: seg.rate || state.doc.meta.rate || "+0%" } });
        renderSent(r.sentences); audio.src = r.audio_url; audio.classList.remove("hidden"); audio.play().catch(() => {});
        toast(`내레이션 ${r.duration.toFixed(1)}초, ${r.sentences.length}문장`);
      } catch (e) { toast(e.message, "bad"); }
      btnTts.disabled = false; btnTts.textContent = "▶ 듣기 · 문장 타이밍";
    } }, "▶ 듣기 · 문장 타이밍");
    narr.append(el("div", { class: "row" }, el("label", { class: "hint" }, "내레이션"), el("span", { class: "spacer" }), audio, btnTts), ta, sentBox);
    pane.append(narr);
    renderSent();

    // 액션
    const addSel = el("select", {});
    addSel.append(el("option", { value: "" }, "+ 액션 추가…"));
    let lastCat = null;
    for (const a of state.catalog) {
      if (a.category !== lastCat) { lastCat = a.category; addSel.append(el("optgroup", { label: a.category })); }
      addSel.lastChild.append(el("option", { value: a.name }, `${a.name} — ${a.doc}`.slice(0, 70)));
    }
    addSel.addEventListener("change", () => {
      if (!addSel.value) return;
      const t = state.catalogByName[addSel.value];
      seg.actions.push({ do: addSel.value, ...(JSON.parse(JSON.stringify(t.template || {}))) });
      touched(); renderSegEditor(); renderSegList();
    });
    pane.append(el("div", { class: "actions-head" }, el("h3", {}, `액션 ${seg.actions.length}개`), el("span", { class: "spacer" }), addSel));
    seg.actions.forEach((act, i) => pane.append(actionCard(seg, act, i)));
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

  // ------------------------------------------------------------------ 액션 카드
  function actionCard(seg, act, i) {
    const spec = state.catalogByName[act.do];
    const card = el("div", { class: "card" });
    const nSent = splitSentences(seg.narration).length;
    if (typeof act.at === "string" && /^s\d+$/.test(act.at) && Number(act.at.slice(1)) > Math.max(1, nSent)) card.classList.add("at-warn");

    const doSel = el("select", { class: "do" });
    let lastCat = null;
    for (const a of state.catalog) {
      if (a.category !== lastCat) { lastCat = a.category; doSel.append(el("optgroup", { label: a.category })); }
      doSel.lastChild.append(el("option", { value: a.name }, a.name));
    }
    if (!spec) doSel.append(el("option", { value: act.do }, act.do + " (?)"));
    doSel.value = act.do;
    doSel.addEventListener("change", () => { act.do = doSel.value; touched(); rerenderCard(); });

    const atIn = el("input", { class: "at", value: act.at ?? "", placeholder: "s2 / 3.5", title: "실행 시각: sN(문장 N 시작) 또는 초" });
    atIn.addEventListener("change", () => { const v = parseVal(atIn.value); if (v === undefined) delete act.at; else act.at = v; touched(); rerenderCard(); });
    const rtIn = el("input", { class: "rt", value: act.run_time ?? "", placeholder: "run", title: "run_time(초)" });
    rtIn.addEventListener("change", () => { const v = parseVal(rtIn.value); if (v === undefined) delete act.run_time; else act.run_time = v; touched(); });

    const head = el("div", { class: "head" },
      el("span", { class: "idx" }, String(i + 1)), doSel,
      el("span", { class: "doc", title: spec?.doc_full || "" }, spec ? spec.doc : "알 수 없는 액션"),
      el("label", {}, "at"), atIn, el("label", {}, "run"), rtIn,
      el("button", { class: "ghost mini", title: "위로", onclick: () => swapAct(seg, i, -1) }, "↑"),
      el("button", { class: "ghost mini", title: "아래로", onclick: () => swapAct(seg, i, 1) }, "↓"),
      el("button", { class: "ghost mini", title: "복제", onclick: () => { seg.actions.splice(i + 1, 0, JSON.parse(JSON.stringify(act))); touched(); renderSegEditor(); renderSegList(); } }, "⧉"),
      el("button", { class: "ghost mini", title: "삭제", onclick: () => { seg.actions.splice(i, 1); touched(); renderSegEditor(); renderSegList(); } }, "✕"));
    card.append(head);

    // 파라미터 그리드
    const params = el("div", { class: "params" });
    const skip = new Set(["do", "at", "run_time", "steps", "parts"]);
    const known = (spec?.params || []).map((p) => p.name).filter((n) => !skip.has(n));
    const extra = Object.keys(act).filter((k) => !skip.has(k) && !known.includes(k));
    const handledByStepsEditor = act.do === "derive" || act.do === "step";
    const keys = [...known, ...extra].filter((k) => !(handledByStepsEditor && ["why", "from", "focus", "new", "cancel", "box", "pulse", "hold", "cancel_at", "underline", "same_line", "space"].includes(k) && act.do === "step"));
    for (const k of keys) {
      const pspec = (spec?.params || []).find((p) => p.name === k);
      const val = act[k];
      const input = el("input", { value: val === undefined ? "" : fmtVal(val), placeholder: pspec && pspec.default !== null && pspec.default !== undefined ? `기본 ${fmtVal(pspec.default)}` : "" });
      if (val !== undefined && typeof val !== "string") input.classList.add("json");
      input.addEventListener("change", () => {
        const v = parseVal(input.value);
        if (v === undefined) delete act[k]; else act[k] = v;
        input.classList.toggle("json", v !== undefined && typeof v !== "string");
        touched();
      });
      if (k === "fn" && act.do === "custom" && state.hooks.length) {
        input.setAttribute("list", "hooksList");
      }
      if (k === "section" && act.do === "goto") input.setAttribute("list", "sectionsList");
      params.append(el("span", { class: "k" + (pspec?.required ? " req" : ""), title: pspec?.type || "" }, k), input,
        el("span", { class: "x", title: "값 지우기", onclick: () => { delete act[k]; touched(); rerenderCard(); } }, "✕"));
    }
    card.append(params);
    ensureDatalists();

    // derive/step 전용: 단계 편집기
    if (act.do === "derive") card.append(stepsEditor(act.steps = act.steps || [], () => { touched(); }));
    if (act.do === "step") card.append(stepsEditor([act], () => { touched(); }, true));

    // 푸터: 항목 추가 / JSON
    const newKey = el("input", { placeholder: "항목 추가 (키)", style: "width:150px" });
    newKey.addEventListener("keydown", (e) => { if (e.key === "Enter" && newKey.value.trim()) { act[newKey.value.trim()] = ""; touched(); rerenderCard(); } });
    const rawBtn = el("button", { class: "ghost mini", onclick: () => { state.rawOpen.has(act) ? state.rawOpen.delete(act) : state.rawOpen.add(act); rerenderCard(); } }, state.rawOpen.has(act) ? "JSON 닫기" : "JSON");
    card.append(el("div", { class: "foot" }, newKey, el("span", { class: "hint" }, "값: 숫자/true/false/[목록]/{매핑} 은 자동 인식, 나머지는 문자열"), rawBtn));
    if (state.rawOpen.has(act)) {
      const ta = el("textarea", { class: "raw", spellcheck: "false" });
      ta.value = JSON.stringify(act, null, 2);
      ta.addEventListener("change", () => {
        try { const o = JSON.parse(ta.value); for (const k of Object.keys(act)) delete act[k]; Object.assign(act, o); touched(); rerenderCard(); }
        catch (e) { toast("JSON 오류: " + e.message, "bad"); }
      });
      card.append(ta);
    }

    function rerenderCard() { const n = actionCard(seg, act, i); card.replaceWith(n); }
    return card;
  }

  function swapAct(seg, i, d) {
    const j = i + d; if (j < 0 || j >= seg.actions.length) return;
    [seg.actions[i], seg.actions[j]] = [seg.actions[j], seg.actions[i]]; touched(); renderSegEditor();
  }

  function ensureDatalists() {
    let dl = $("#hooksList");
    if (!dl) { dl = el("datalist", { id: "hooksList" }); document.body.append(dl); }
    dl.innerHTML = ""; for (const h of state.hooks) dl.append(el("option", { value: h }));
    let sl = $("#sectionsList");
    if (!sl) { sl = el("datalist", { id: "sectionsList" }); document.body.append(sl); }
    sl.innerHTML = ""; for (const s of (state.doc.layout?.chalk?.sections || [])) sl.append(el("option", { value: s.id }));
  }

  /** derive.steps 또는 step 액션 하나를 편집하는 표. single=true 면 steps 배열 대신 액션 자체가 한 단계. */
  function stepsEditor(steps, onchange, single = false) {
    const box = el("div", { class: "steps" });
    const render = () => {
      box.innerHTML = "";
      box.append(el("div", { class: "row" }, el("span", { class: "hint" }, single ? "단계 내용" : `전개 단계 ${steps.length}개 — 조각은 " | " 로 구분 (예: = | 2^{3} | \\times | x)`),
        el("span", { class: "spacer" }),
        single ? null : el("button", { class: "ghost mini", onclick: () => { steps.push({ parts: ["=", ""] }); onchange(); render(); } }, "+ 단계")));
      steps.forEach((st, k) => {
        const partsIn = el("input", { value: joinParts(st.parts || (st.tex ? [st.tex] : [])), placeholder: "조각 | 조각 | …" });
        partsIn.addEventListener("change", () => { st.parts = splitParts(partsIn.value); delete st.tex; onchange(); });
        const whyIn = el("input", { value: st.why || "", placeholder: "(∵ 이유)" });
        whyIn.addEventListener("change", () => { if (whyIn.value.trim()) st.why = whyIn.value; else delete st.why; onchange(); });
        const row = el("div", { class: "step" }, el("span", { class: "n" }, single ? "" : String(k + 1)), partsIn, whyIn,
          single ? el("span") : el("span", {},
            el("button", { class: "ghost mini", onclick: () => { if (k > 0) { [steps[k - 1], steps[k]] = [steps[k], steps[k - 1]]; onchange(); render(); } } }, "↑"),
            el("button", { class: "ghost mini", onclick: () => { steps.splice(k, 1); onchange(); render(); } }, "✕")));
        // 옵션 줄
        const opts = el("div", { class: "opts" });
        const chk = (key, label) => { const c = el("input", { type: "checkbox" }); c.checked = !!st[key]; c.addEventListener("change", () => { if (c.checked) st[key] = true; else delete st[key]; onchange(); }); return el("label", {}, c, label); };
        const txt = (key, label, cls = "small", ph = "") => { const t = el("input", { class: cls, value: st[key] === undefined ? "" : fmtVal(st[key]), placeholder: ph }); t.addEventListener("change", () => { const v = parseVal(t.value); if (v === undefined) delete st[key]; else st[key] = v; onchange(); }); return el("label", {}, label, t); };
        opts.append(txt("at", "at", "small", "s2"), txt("hold", "hold", "small", "s3"), txt("run_time", "run", "small", "2.0"),
          chk("box", "상자"), chk("pulse", "펄스"),
          txt("from", "from", "wide", '{"2^{2}": "x^{2}"}'), txt("cancel", "cancel", "wide", '["a_7", 5]'),
          txt("cancel_at", "cancel_at", "small", "s5"), txt("focus", "focus", "wide", '["2\\\\cdot3x^{2}"]'), txt("new", "new", "wide", '["6", "x^{2}"]'));
        row.append(opts);
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
