import { loadProject, saveProject, newProject, toYaml } from "./store.js";
import { ChalkCanvas } from "./board.js";
import { BeatPlayer } from "./player.js";
import { BeatEditor } from "./editor.js";
import { BoardRecorder } from "./recorder.js";

const project = loadProject();
const canvas = document.getElementById("board");
const board = new ChalkCanvas(canvas);
const player = new BeatPlayer(board, project);
const editor = new BeatEditor(project, document.getElementById("beat-list"), document.getElementById("beat-form"), {
  onChange: persist,
  onPreviewStatic: drawStaticPreview,
});

let recorder = null;

function persist() {
  saveProject(project);
  document.getElementById("project-title").textContent = project.title;
  document.getElementById("exp-title").value = project.title;
  document.getElementById("exp-answer").value = project.answer || "";
}

async function drawStaticPreview() {
  board.clear();
  board.setHeader(project.brand, project.title);
  for (const b of project.beats) {
    if (b.type === "say") {
      const p = b.link === "therefore" ? "⇒ " : b.link === "when" ? "→ " : "";
      board.setCaption(p + (b.text || ""));
    }
    if (b.type === "math") await board.addMathLine(b.latex || "");
    if (b.type === "graph") board.setGraph(b.graphType || "f_prime", b.title || "");
    if (b.type === "dot") board.addDot(b.x, b.y, b.label, b.color);
  }
  if (!project.beats.length) board.drawFrame();
}

// Tabs
const panels = {
  edit: document.getElementById("panel-edit"),
  play: document.getElementById("panel-edit"),
  record: document.getElementById("panel-record"),
  export: document.getElementById("panel-export"),
};

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", async () => {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    Object.values(panels).forEach((p) => p.classList.add("hidden"));
    const tab = btn.dataset.tab;
    if (tab === "play") {
      panels.edit.classList.remove("hidden");
      await runPreview();
    } else {
      panels[tab].classList.remove("hidden");
    }
  });
});

async function runPreview() {
  const overlay = document.getElementById("play-overlay");
  const status = document.getElementById("play-status");
  overlay.classList.remove("hidden");
  player.onStatus = (s) => { status.textContent = s; };
  player.stop();
  await player.play();
  setTimeout(() => overlay.classList.add("hidden"), 800);
}

// Record
document.getElementById("btn-record").addEventListener("click", async () => {
  const btnRec = document.getElementById("btn-record");
  const btnStop = document.getElementById("btn-stop");
  const dl = document.getElementById("download-link");
  const recStatus = document.getElementById("rec-status");

  try {
    recorder = new BoardRecorder(canvas, board, project);
    recorder.onStatus = (s) => { recStatus.textContent = s; };
    recorder.onTime = (t) => { document.getElementById("rec-time").textContent = t; };

    btnRec.classList.add("hidden");
    btnStop.classList.remove("hidden");
    dl.classList.add("hidden");
    recStatus.textContent = "녹화 중…";

    const { blob, mime } = await recorder.start();
    const ext = mime.includes("mp4") ? "mp4" : "webm";
    const url = URL.createObjectURL(blob);
    dl.href = url;
    dl.download = `lecture-${Date.now()}.${ext}`;
    dl.classList.remove("hidden");
    recStatus.textContent = "완료 — 저장하세요";
  } catch (err) {
    recStatus.textContent = err.message || "녹화 실패";
  } finally {
    btnRec.classList.remove("hidden");
    btnStop.classList.add("hidden");
  }
});

document.getElementById("btn-stop").addEventListener("click", () => recorder?.stop());

// Export
document.getElementById("btn-export-json").addEventListener("click", async () => {
  project.title = document.getElementById("exp-title").value;
  project.answer = document.getElementById("exp-answer").value;
  persist();
  await copyText(JSON.stringify(project, null, 2));
  toast("JSON 복사됨");
});

document.getElementById("btn-export-yaml").addEventListener("click", async () => {
  project.title = document.getElementById("exp-title").value;
  project.answer = document.getElementById("exp-answer").value;
  await copyText(toYaml(project));
  toast("YAML 복사됨");
});

document.getElementById("btn-import").addEventListener("click", () => {
  document.getElementById("import-file").click();
});

document.getElementById("import-file").addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    Object.assign(project, data);
    persist();
    editor.renderList();
    drawStaticPreview();
    toast("불러오기 완료");
  } catch {
    toast("JSON 오류");
  }
});

// Settings
const dlg = document.getElementById("settings-dialog");
document.getElementById("btn-settings").addEventListener("click", () => {
  document.getElementById("set-title").value = project.title;
  document.getElementById("set-brand").value = project.brand;
  dlg.showModal();
});

dlg.querySelector("form").addEventListener("close", () => {
  if (dlg.returnValue === "default") {
    project.title = document.getElementById("set-title").value.trim() || project.title;
    project.brand = document.getElementById("set-brand").value.trim() || project.brand;
    persist();
    drawStaticPreview();
  }
});

document.getElementById("btn-new-project").addEventListener("click", () => {
  if (confirm("현재 프로젝트를 지우고 새로 시작할까요?")) {
    const fresh = newProject();
    Object.assign(project, fresh);
    persist();
    editor.renderList();
    board.clear();
    board.setHeader(project.brand, project.title);
    board.drawFrame();
    dlg.close();
  }
});

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
  } else {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }
}

function toast(msg) {
  const el = document.getElementById("play-status");
  const overlay = document.getElementById("play-overlay");
  el.textContent = msg;
  overlay.classList.remove("hidden");
  setTimeout(() => overlay.classList.add("hidden"), 1500);
}

// Init
persist();
editor.renderList();
board.setHeader(project.brand, project.title);
drawStaticPreview();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
