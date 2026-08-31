import { BeatPlayer } from "./player.js";

export class BoardRecorder {
  constructor(canvas, board, project) {
    this.canvas = canvas;
    this.board = board;
    this.project = project;
    this.recorder = null;
    this.chunks = [];
    this.startTime = 0;
    this.timerId = null;
    this.onStatus = () => {};
    this.onTime = () => {};
  }

  _mimeType() {
    const types = [
      "video/webm;codecs=vp9",
      "video/webm;codecs=vp8",
      "video/webm",
      "video/mp4",
    ];
    return types.find((t) => MediaRecorder.isTypeSupported(t)) || "";
  }

  async start() {
    if (!this.canvas.captureStream) {
      throw new Error("이 브라우저는 canvas 녹화를 지원하지 않습니다.");
    }
    const stream = this.canvas.captureStream(30);
    const mime = this._mimeType();
    if (!mime) throw new Error("MediaRecorder를 지원하지 않습니다.");

    this.chunks = [];
    this.recorder = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 4_000_000 });
    this.recorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.chunks.push(e.data);
    };

    const player = new BeatPlayer(this.board, this.project);
    player.onStatus = (s) => this.onStatus(s);

    this.board.clear();
    this.board.setHeader(this.project.brand, this.project.title);
    this.board.drawFrame();

    return new Promise((resolve, reject) => {
      this.recorder.onstop = () => {
        clearInterval(this.timerId);
        const blob = new Blob(this.chunks, { type: mime });
        resolve({ blob, mime });
      };
      this.recorder.onerror = (e) => reject(e.error || new Error("녹화 오류"));

      this.recorder.start(200);
      this.startTime = Date.now();
      this.timerId = setInterval(() => {
        const sec = Math.floor((Date.now() - this.startTime) / 1000);
        this.onTime(`${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`);
      }, 500);

      player.play().then(() => {
        setTimeout(() => this.stop(), 400);
      });
    });
  }

  stop() {
    if (this.recorder && this.recorder.state !== "inactive") {
      this.recorder.stop();
    }
  }
}
