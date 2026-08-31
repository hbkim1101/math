import { beatBadge, beatLabel } from "./store.js";

export class BeatEditor {
  constructor(project, listEl, formEl, callbacks) {
    this.project = project;
    this.listEl = listEl;
    this.formEl = formEl;
    this.cb = callbacks;
    this.pendingType = "say";
    this.bindToolbar();
    this.bindForm();
  }

  bindToolbar() {
    document.querySelectorAll(".beat-toolbar .chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".beat-toolbar .chip").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.pendingType = btn.dataset.add;
        this.openForm(-1, this.pendingType);
      });
    });
  }

  bindForm() {
    const form = this.formEl;
    document.getElementById("btn-cancel").addEventListener("click", () => this.closeForm());
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      this.saveBeat();
    });
    document.getElementById("inp-math").addEventListener("input", () => this.previewMath());
  }

  previewMath() {
    const el = document.getElementById("math-preview");
    const tex = document.getElementById("inp-math").value;
    if (typeof katex !== "undefined" && tex) {
      try {
        katex.render(tex, el, { throwOnError: false });
      } catch {
        el.textContent = tex;
      }
    } else el.textContent = tex;
  }

  renderList() {
    const beats = this.project.beats;
    this.listEl.innerHTML = "";
    if (!beats.length) {
      this.listEl.innerHTML = '<li class="empty-beats">위 버튼으로 beat를 추가하세요<br>⇒ 말하기 → 수식 → 그래프 → 점</li>';
      return;
    }
    beats.forEach((beat, i) => {
      const li = document.createElement("li");
      li.className = "beat-item";
      li.innerHTML = `
        <span class="beat-badge">${beatBadge(beat)}</span>
        <div class="beat-body">
          <div class="beat-type">${beat.type}</div>
          <div class="beat-text">${escapeHtml(beatLabel(beat))}</div>
        </div>
        <div class="beat-actions">
          <button type="button" data-up="${i}" aria-label="위로">↑</button>
          <button type="button" data-edit="${i}" aria-label="편집">✎</button>
          <button type="button" data-del="${i}" aria-label="삭제">✕</button>
        </div>`;
      this.listEl.appendChild(li);
    });

    this.listEl.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", () => this.openForm(+btn.dataset.edit));
    });
    this.listEl.querySelectorAll("[data-del]").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.project.beats.splice(+btn.dataset.del, 1);
        this.cb.onChange();
        this.renderList();
      });
    });
    this.listEl.querySelectorAll("[data-up]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = +btn.dataset.up;
        if (i > 0) {
          [this.project.beats[i - 1], this.project.beats[i]] = [this.project.beats[i], this.project.beats[i - 1]];
          this.cb.onChange();
          this.renderList();
        }
      });
    });
  }

  openForm(index, typeOverride) {
    const type = typeOverride || (index >= 0 ? this.project.beats[index].type : this.pendingType);
    const beat = index >= 0 ? this.project.beats[index] : { type };

    document.getElementById("edit-index").value = index;
    document.getElementById("form-title").textContent = index >= 0 ? "Beat 편집" : "Beat 추가";

    const fields = ["field-link", "field-text", "field-math", "field-graph", "field-dot", "field-wait"];
    fields.forEach((id) => document.getElementById(id).classList.add("hidden"));

    if (type === "say") {
      document.getElementById("field-link").classList.remove("hidden");
      document.getElementById("field-text").classList.remove("hidden");
      document.getElementById("inp-link").value = beat.link || "therefore";
      document.getElementById("inp-text").value = beat.text || "";
    } else if (type === "math") {
      document.getElementById("field-math").classList.remove("hidden");
      document.getElementById("inp-math").value = beat.latex || "";
      this.previewMath();
    } else if (type === "graph") {
      document.getElementById("field-graph").classList.remove("hidden");
      document.getElementById("inp-graph-type").value = beat.graphType || "f_prime";
    } else if (type === "dot") {
      document.getElementById("field-dot").classList.remove("hidden");
      document.getElementById("inp-dot-x").value = beat.x ?? 0;
      document.getElementById("inp-dot-y").value = beat.y ?? 0;
      document.getElementById("inp-dot-label").value = beat.label || "";
    } else if (type === "wait") {
      document.getElementById("field-wait").classList.remove("hidden");
      document.getElementById("inp-wait").value = beat.seconds ?? 1;
    }

    this.formEl.classList.remove("hidden");
    this.formEl.dataset.type = type;
  }

  closeForm() {
    this.formEl.classList.add("hidden");
  }

  saveBeat() {
    const type = this.formEl.dataset.type;
    const index = +document.getElementById("edit-index").value;
    let beat = { type };

    if (type === "say") {
      beat.link = document.getElementById("inp-link").value;
      beat.text = document.getElementById("inp-text").value.trim();
    } else if (type === "math") {
      beat.latex = document.getElementById("inp-math").value.trim();
    } else if (type === "graph") {
      beat.graphType = document.getElementById("inp-graph-type").value;
      beat.title = beat.graphType === "f_prime" ? "y=f'(x)" : "";
    } else if (type === "dot") {
      beat.x = parseFloat(document.getElementById("inp-dot-x").value) || 0;
      beat.y = parseFloat(document.getElementById("inp-dot-y").value) || 0;
      beat.label = document.getElementById("inp-dot-label").value.trim();
      beat.color = "yellow";
    } else if (type === "wait") {
      beat.seconds = parseFloat(document.getElementById("inp-wait").value) || 1;
    }

    if (index >= 0) this.project.beats[index] = beat;
    else this.project.beats.push(beat);

    this.cb.onChange();
    this.renderList();
    this.closeForm();
    this.cb.onPreviewStatic();
  }
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
