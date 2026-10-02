// Turn any recording the browser can decode into 16 kHz mono 16-bit WAV,
// which is what Gemma 4's audio encoder expects. Runs entirely on the phone.
window.toWav16k = async function toWav16k(blob) {
  const buf = await blob.arrayBuffer();
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = new Ctx();
  const decoded = await ctx.decodeAudioData(buf);
  ctx.close();

  const rate = 16000;
  const maxSeconds = 30; // a question, not a podcast
  const length = Math.min(Math.ceil(decoded.duration * rate), rate * maxSeconds);
  const off = new OfflineAudioContext(1, length, rate);
  const src = off.createBufferSource();
  src.buffer = decoded;
  src.connect(off.destination);
  src.start();
  const pcm = (await off.startRendering()).getChannelData(0);

  const out = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const str = (o, s) => [...s].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)));
  str(0, "RIFF"); out.setUint32(4, 36 + pcm.length * 2, true); str(8, "WAVE");
  str(12, "fmt "); out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, 1, true);
  out.setUint32(24, rate, true); out.setUint32(28, rate * 2, true); out.setUint16(32, 2, true); out.setUint16(34, 16, true);
  str(36, "data"); out.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) {
    const s = Math.max(-1, Math.min(1, pcm[i]));
    out.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([out], { type: "audio/wav" });
};

// In-page recording needs a secure context (localhost or HTTPS). On plain-HTTP
// home Wi-Fi the app falls back to the phone's own recorder via a file input.
window.canRecordInPage = () =>
  window.isSecureContext && !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) && !!window.MediaRecorder;

window.Recorder = class {
  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.chunks = [];
    this.rec = new MediaRecorder(this.stream);
    this.rec.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
    this.done = new Promise((r) => (this.rec.onstop = r));
    this.rec.start();
  }
  async stop() {
    this.rec.stop();
    await this.done;
    this.stream.getTracks().forEach((t) => t.stop());
    return new Blob(this.chunks, { type: this.rec.mimeType });
  }
};
