const STORAGE_KEY = "hansu-studio-project-v1";

const SAMPLE = {
  title: "15번 · 미분·조각함수",
  brand: "수학 한수",
  answer: "① 15/4",
  beats: [
    { type: "say", link: "therefore", text: "우미분계수가 실수이려면 분자→0" },
    { type: "math", latex: String.raw`\lim_{x\to a^+}\frac{g(x)-g(a)}{x-a}\in\mathbb{R}` },
    { type: "say", link: "therefore", text: "x=a에서 우연속" },
    { type: "math", latex: String.raw`\lim_{x\to a^+}g(x)=g(a)` },
    { type: "say", link: "therefore", text: "f'(x) 그래프부터" },
    { type: "graph", graphType: "f_prime", title: "y=f'(x)" },
    { type: "dot", x: -1, y: 0, label: "" },
    { type: "dot", x: 1, y: 0, label: "" },
    { type: "dot", x: 0, y: 6, label: "(0,6)", color: "pink" },
    { type: "say", link: "therefore", text: "정답 ① 15/4" },
    { type: "math", latex: String.raw`k+f\!\left(\tfrac12\right)=\tfrac{15}{4}` },
    { type: "wait", seconds: 1.5 },
  ],
};

export function loadProject() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (_) {
    /* ignore */
  }
  return structuredClone(SAMPLE);
}

export function saveProject(project) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(project));
}

export function newProject() {
  return {
    title: "새 강의",
    brand: "수학 한수",
    answer: "",
    beats: [],
  };
}

export function beatLabel(beat) {
  switch (beat.type) {
    case "say":
      return beat.text || "(빈 설명)";
    case "math":
      return beat.latex || "(수식)";
    case "graph":
      return `그래프: ${beat.graphType || "f_prime"}`;
    case "dot":
      return `점 (${beat.x}, ${beat.y})`;
    case "wait":
      return `${beat.seconds || 1}초 대기`;
    default:
      return beat.type;
  }
}

export function beatBadge(beat) {
  if (beat.type === "say") {
    if (beat.link === "when") return "→";
    if (beat.link === "therefore") return "⇒";
    return "·";
  }
  const map = { math: "fx", graph: "📈", dot: "•", wait: "⏸" };
  return map[beat.type] || "?";
}

export function toYaml(project) {
  const lines = [
    `# ${project.title}`,
    `brand: "${project.brand}"`,
    `answer: "${project.answer}"`,
    "flow:",
  ];
  for (const b of project.beats) {
    if (b.type === "say") {
      lines.push(`  - link: ${b.link === "when" ? "when" : "therefore"}`);
      lines.push(`    caption: "${b.text.replace(/"/g, '\\"')}"`);
    } else if (b.type === "math") {
      lines.push("  - link: therefore");
      lines.push(`    math: '${b.latex.replace(/'/g, "''")}'`);
    } else if (b.type === "graph") {
      lines.push("  - link: therefore");
      lines.push("    visual:");
      lines.push("      type: graph");
      lines.push(`      graph: ${b.graphType}`);
    } else if (b.type === "dot") {
      lines.push("      annotate:");
      lines.push("        - action: dot");
      lines.push(`          at: [${b.x}, ${b.y}]`);
      if (b.label) lines.push(`          label: "${b.label}"`);
    }
  }
  return lines.join("\n");
}
