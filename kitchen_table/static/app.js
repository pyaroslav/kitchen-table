// Kitchen Table — phone UI. No framework, no CDN: it has to work with the internet off.
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const view = $("#view");
const ICONS = { file_it: "✓", action_needed: "✎", urgent: "!", scam_warning: "⚠" };

const store = {
  get(k, d) { try { return localStorage.getItem("kt." + k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem("kt." + k, v); } catch { /* private mode: fine */ } },
};

const state = { T: {}, languages: {}, pages: [], status: null };
const settings = () => ({
  lang: store.get("lang", ""),
  helper: store.get("helper", ""),
  helperLang: store.get("helperLang", "en"),
});

function t(key, vars = {}) {
  let s = state.T[key] ?? key;
  const helper = settings().helper || state.T.family || "family";
  vars = { helper, ...vars };
  for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, v);
  return s;
}

function applyStrings(root) {
  root.querySelectorAll("[data-t]").forEach((el) => (el.textContent = t(el.dataset.t)));
  root.querySelectorAll("[data-ph]").forEach((el) => (el.placeholder = t(el.dataset.ph)));
}

function toast(msg, ms = 2600) {
  const el = $("#toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), ms);
}

function speechTag(code) { return state.languages[code]?.speech || "en-US"; }

async function loadLanguage(code) {
  const lang = code || "en";
  try {
    state.T = await (await fetch(`/api/ui/${lang}`)).json();
  } catch {
    state.T = await (await fetch("/i18n/en.json")).json();
  }
  const rtl = !!state.languages[lang]?.rtl;
  document.documentElement.lang = lang;
  document.documentElement.dir = rtl ? "rtl" : "ltr";
  applyStrings(document);
  $("#appName").textContent = t("app_name");
  document.title = t("app_name");
}

function mount(tplId) {
  const node = $(tplId).content.cloneNode(true);
  applyStrings(node);
  view.replaceChildren(node);
  window.scrollTo(0, 0);
}

// ---------- routing ----------
async function route() {
  speechSynthesis?.cancel();
  const hash = location.hash || "#/";
  $("#backBtn").hidden = hash === "#/" || hash === "";
  if (!settings().lang || hash === "#/setup") return renderSetup();
  const m = hash.match(/^#\/letter\/(\w+)/);
  if (m) return renderLetter(m[1]);
  return renderHome();
}

// ---------- setup ----------
function renderSetup() {
  mount("#tpl-setup");
  const s = settings();
  let chosen = s.lang || "en";
  const grid = $("#langGrid");
  const helperLang = $("#helperLang");
  for (const [code, l] of Object.entries(state.languages)) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = l.native;
    b.lang = code;
    b.setAttribute("aria-pressed", code === chosen);
    b.onclick = async () => {
      chosen = code;
      grid.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      await loadLanguage(code);
      applyStrings(view);
    };
    grid.append(b);
    helperLang.append(new Option(`${l.native} (${l.name})`, code, false, code === s.helperLang));
  }
  $("#helperName").value = s.helper;
  $("#saveSetup").onclick = () => {
    store.set("lang", chosen);
    store.set("helper", $("#helperName").value.trim());
    store.set("helperLang", helperLang.value);
    location.hash = "#/";
    route();
  };
}

// ---------- home ----------
async function renderHome() {
  mount("#tpl-home");
  $("#cameraBtn").onclick = () => $("#photoInput").click();
  $("#addPage").onclick = () => $("#photoInput").click();
  $("#explainBtn").onclick = explain;
  drawTray();

  const list = $("#letterList");
  let letters = [];
  try { letters = await (await fetch("/api/letters")).json(); } catch { /* offline server */ }
  if (!letters.length) {
    list.innerHTML = `<li class="empty">${t("none_yet")}</li>`;
    return;
  }
  for (const l of letters) {
    const li = document.createElement("li");
    const nd = l.next_deadline;
    const when = nd ? ` · ${fmtDate(nd.date)}` : "";
    li.innerHTML = `<a href="#/letter/${l.id}" class="${l.handled ? "handled" : ""}">
        <span class="dot ${l.verdict}"></span>
        <span><span class="l-head"></span><br><span class="l-sub"></span></span></a>`;
    $(".l-head", li).textContent = l.headline || "…";
    $(".l-sub", li).textContent = (l.sender || "") + when + (l.handled ? ` · ${t("done")}` : "");
    list.append(li);
  }
}

function drawTray() {
  const tray = $("#pagesTray");
  if (!tray) return;
  tray.hidden = state.pages.length === 0;
  $("#cameraBtn").hidden = state.pages.length > 0;
  $(".tray-count", tray).textContent = t("pages", { n: state.pages.length });
  const thumbs = $(".thumbs", tray);
  thumbs.replaceChildren();
  state.pages.forEach((file, i) => {
    const d = document.createElement("div");
    d.className = "thumb";
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    img.alt = `${i + 1}`;
    const x = document.createElement("button");
    x.textContent = "×";
    x.setAttribute("aria-label", t("remove"));
    x.onclick = () => { state.pages.splice(i, 1); drawTray(); };
    d.append(img, x);
    thumbs.append(d);
  });
}

$("#photoInput").addEventListener("change", (e) => {
  const f = e.target.files[0];
  e.target.value = "";
  if (!f) return;
  state.pages.push(f);
  drawTray();
});

async function explain() {
  if (!state.pages.length) return;
  mount("#tpl-working");
  const msgs = ["reading", "explaining", "almost"];
  let i = 0;
  const started = Date.now();
  const tick = () => {
    $("#workingMsg").textContent = t(msgs[Math.min(i, msgs.length - 1)]);
    $("#workingSub").textContent = t("seconds", { n: Math.round((Date.now() - started) / 1000) });
  };
  tick();
  const timer = setInterval(() => { tick(); }, 1000);
  const stepper = setInterval(() => i++, 9000);

  const s = settings();
  const fd = new FormData();
  state.pages.forEach((p) => fd.append("pages", p));
  fd.append("lang", s.lang);
  fd.append("helper_lang", s.helperLang);
  try {
    const r = await fetch("/api/letters", { method: "POST", body: fd });
    if (r.status === 503) throw new Error(t("error_model"));
    if (!r.ok) throw new Error(t("error_read"));
    const letter = await r.json();
    state.pages = [];
    location.hash = `#/letter/${letter.id}`;
  } catch (err) {
    toast(err.message || t("error_read"), 6000);
    renderHome();
  } finally {
    clearInterval(timer);
    clearInterval(stepper);
  }
}

// ---------- one letter ----------
function fmtDate(iso, opts = { month: "long", day: "numeric", year: "numeric" }) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat(speechTag(settings().lang), opts).format(new Date(y, m - 1, d));
}

function daysText(n) {
  if (n === 0) return t("today");
  if (n === 1) return t("tomorrow");
  if (n < 0) return t("overdue", { n: -n });
  return t("days_left", { n });
}

function fmtMoney(m) {
  try {
    return new Intl.NumberFormat(speechTag(settings().lang), { style: "currency", currency: m.currency || "USD" }).format(m.amount);
  } catch {
    return `${m.amount} ${m.currency || ""}`;
  }
}

async function renderLetter(id) {
  const r = await fetch(`/api/letters/${id}`);
  if (!r.ok) { location.hash = "#/"; return; }
  const L = await r.json();
  const a = L.analysis;
  const scam = a.verdict === "scam_warning";
  mount("#tpl-letter");

  const v = $("#verdict");
  v.classList.add(a.verdict);
  $(".verdict-icon", v).textContent = ICONS[a.verdict] || "•";
  $(".verdict-label", v).textContent = t("v_" + a.verdict);
  if (scam) { $("#scamAdvice").hidden = false; $("#scamAdvice").textContent = t("scam_advice"); }

  $("#sender").textContent = a.sender || "?";
  $("#headline").textContent = a.headline;
  $("#summary").textContent = a.summary;
  if (a.confidence === "low") { $("#lowConf").hidden = false; $("#lowConf").textContent = t("low_confidence"); }

  const steps = $("#steps");
  if (!a.steps?.length) steps.outerHTML = `<p>${t("nothing_to_do")}</p>`;
  for (const s of a.steps || []) {
    const li = document.createElement("li");
    li.textContent = s.text;
    if (s.by_date) {
      const by = document.createElement("span");
      by.className = "by";
      by.textContent = t("by", { date: fmtDate(s.by_date) });
      li.append(by);
    }
    steps.append(li);
  }

  if (a.deadlines?.length && !scam) {
    $("#datesCard").hidden = false;
    $("#icsLink").href = `/api/letters/${id}/calendar.ics`;
    for (const d of a.deadlines) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="cal"><span class="m"></span><span class="d"></span></span>
        <span><span class="left"></span><span class="what"></span></span>`;
      $(".m", li).textContent = fmtDate(d.date, { month: "short" });
      $(".d", li).textContent = fmtDate(d.date, { day: "numeric" });
      $(".left", li).textContent = daysText(d.days_left);
      $(".left", li).classList.toggle("soon", d.days_left <= 7);
      $(".what", li).textContent = d.what;
      $("#dates").append(li);
    }
  }

  const m = a.money || {};
  if (m.amount != null && m.direction !== "none" && !scam) {
    $("#moneyCard").hidden = false;
    $("#money").innerHTML = `<small></small><span></span><small class="ap"></small>`;
    $("#money small").textContent = t(m.direction);
    $("#money span").textContent = fmtMoney(m);
    if (m.already_paid_or_autopay) $("#money .ap").textContent = t("autopay");
  }

  if (a.scam_signals?.length) {
    $("#signsCard").hidden = false;
    for (const s of a.scam_signals) {
      const li = document.createElement("li");
      li.textContent = s;
      $("#signs").append(li);
    }
  }

  if (a.glossary?.length) {
    $("#wordsCard").hidden = false;
    for (const g of a.glossary) {
      const dt = document.createElement("dt"); dt.textContent = g.term; dt.lang = "en";
      const dd = document.createElement("dd"); dd.textContent = g.meaning;
      $("#words").append(dt, dd);
    }
  }

  if (a.contacts?.length) {
    $("#contactsCard").hidden = false;
    for (const c of a.contacts) {
      const li = document.createElement("li");
      li.append(c.label + ": ");
      // Never make a suspected scammer's number one tap away.
      if (c.phone) li.append(scam ? Object.assign(document.createElement("span"), { className: "nolink", textContent: c.phone })
                                  : Object.assign(document.createElement("a"), { href: "tel:" + c.phone.replace(/[^\d+]/g, ""), textContent: c.phone }));
      if (c.website) li.append(" ", Object.assign(document.createElement("span"), { textContent: c.website }));
      $("#contacts").append(li);
    }
  }

  // read aloud
  const speakBtn = $("#speakBtn");
  if (!("speechSynthesis" in window)) speakBtn.hidden = true;
  speakBtn.onclick = () => {
    if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }
    const parts = [t("v_" + a.verdict), scam ? t("scam_advice") : "", a.headline, a.summary,
                   ...(a.steps || []).map((s, i) => `${i + 1}. ${s.text}`)];
    const u = new SpeechSynthesisUtterance(parts.filter(Boolean).join(". "));
    u.lang = speechTag(settings().lang);
    u.rate = 0.92;
    speechSynthesis.speak(u);
  };

  // questions
  const qa = $("#qa");
  const addTurn = (q, ans) => {
    const qe = document.createElement("p"); qe.className = "q"; qe.textContent = q;
    const ae = document.createElement("p"); ae.className = "a"; ae.textContent = ans;
    qa.append(qe, ae);
    return ae;
  };
  L.qa.forEach((x) => addTurn(x.question, x.answer));

  const ask = async (question, audioBlob) => {
    const pending = addTurn(question || "🎤 …", t("thinking"));
    const fd = new FormData();
    fd.append("lang", settings().lang);
    if (question) fd.append("question", question);
    if (audioBlob) fd.append("audio", audioBlob, "q.wav");
    try {
      const r = await fetch(`/api/letters/${id}/ask`, { method: "POST", body: fd });
      if (!r.ok) throw new Error(r.status === 503 ? t("error_model") : "error");
      const out = await r.json();
      pending.previousSibling.textContent = out.question;
      pending.textContent = out.answer;
      if ("speechSynthesis" in window) {
        const u = new SpeechSynthesisUtterance(out.answer);
        u.lang = speechTag(settings().lang);
        u.rate = 0.92;
        speechSynthesis.speak(u);
      }
    } catch (e) {
      pending.textContent = e.message === "error" ? t("error_read") : e.message;
    }
  };

  $("#askForm").onsubmit = (e) => {
    e.preventDefault();
    const q = $("#askInput").value.trim();
    if (!q) return;
    $("#askInput").value = "";
    ask(q);
  };

  const mic = $("#micBtn");
  let rec = null;
  mic.onclick = async () => {
    if (!canRecordInPage()) { $("#audioInput").click(); return; }
    if (!rec) {
      try {
        rec = new Recorder();
        await rec.start();
        mic.classList.add("recording");
        $("span:last-child", mic).textContent = t("recording");
      } catch { rec = null; $("#audioInput").click(); }
      return;
    }
    const blob = await rec.stop();
    rec = null;
    mic.classList.remove("recording");
    $("span:last-child", mic).textContent = t("speak");
    ask(null, await toWav16k(blob));
  };
  $("#audioInput").onchange = async (e) => {
    const f = e.target.files[0];
    e.target.value = "";
    if (f) ask(null, await toWav16k(f));
  };

  // share with the helper
  const share = $("#shareBtn");
  share.textContent = "📤 " + t("send_helper");
  share.onclick = async () => {
    const lines = [a.family_note];
    if (a.deadlines?.length) lines.push(a.deadlines.map((d) => `${d.date}: ${d.what}`).join("\n"));
    const text = lines.filter(Boolean).join("\n\n");
    if (navigator.share) {
      try { await navigator.share({ text }); return; } catch { /* cancelled */ return; }
    }
    location.href = "sms:?&body=" + encodeURIComponent(text);
  };

  // done
  const done = $("#doneBtn");
  const drawDone = (h) => {
    done.textContent = h ? t("done") : t("mark_done");
    done.classList.toggle("is-done", h);
  };
  let handled = L.handled;
  drawDone(handled);
  done.onclick = async () => {
    handled = !handled;
    drawDone(handled);
    await fetch(`/api/letters/${id}/handled`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ handled }),
    });
  };

  $("#transcript").textContent = L.transcript;
  $("#meta").textContent = `${L.timing.model} · ${L.timing.read_seconds}s + ${L.timing.explain_seconds}s` +
    (a.overrides?.length ? ` · override: ${a.overrides.join(", ")} (model said ${a.model_verdict})` : "");
  $("#deleteBtn").onclick = async () => {
    await fetch(`/api/letters/${id}`, { method: "DELETE" });
    location.hash = "#/";
  };
}

// ---------- boot ----------
$("#backBtn").onclick = () => { location.hash = "#/"; };
$("#settingsBtn").onclick = () => { location.hash = "#/setup"; };
window.addEventListener("hashchange", route);

(async () => {
  try {
    state.status = await (await fetch("/api/status")).json();
    state.languages = state.status.languages;
  } catch { state.languages = { en: { name: "English", native: "English", speech: "en-US" } }; }
  await loadLanguage(settings().lang || "en");
  if (state.status && !state.status.ok) toast(t("error_model"), 8000);
  route();
})();
