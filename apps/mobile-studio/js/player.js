import { sleep } from "./board.js";

export class BeatPlayer {
  constructor(board, project) {
    this.board = board;
    this.project = project;
    this.running = false;
    this.onStatus = () => {};
  }

  stop() {
    this.running = false;
  }

  async play(fromIndex = 0) {
    this.running = true;
    this.board.clear();
    this.board.setHeader(this.project.brand, this.project.title);
    this.board.drawFrame();

    const beats = this.project.beats;
    for (let i = fromIndex; i < beats.length; i++) {
      if (!this.running) break;
      const b = beats[i];
      this.onStatus(`${i + 1}/${beats.length}: ${b.type}`);

      switch (b.type) {
        case "say": {
          const prefix = b.link === "when" ? "→ " : b.link === "therefore" ? "⇒ " : "";
          await this.board.animateCaption(prefix + (b.text || ""), 35);
          await sleep(500);
          break;
        }
        case "math":
          await this.board.addMathLine(b.latex || "");
          await sleep(700);
          break;
        case "graph":
          await this.board.animateGraph(b.graphType || "f_prime", b.title || "", 1100);
          await sleep(400);
          break;
        case "dot":
          await this.board.animateDot(b.x ?? 0, b.y ?? 0, b.label || "", b.color || "yellow");
          await sleep(350);
          break;
        case "wait":
          await sleep((b.seconds || 1) * 1000);
          break;
        default:
          await sleep(300);
      }
    }

    this.running = false;
    this.onStatus("완료");
  }
}
