/* Офлайн-очередь, пакет дня, индикатор «учимся без интернета» (IMP-OFF-4…6). */
(function () {
  const DB_NAME = "masya-offline";
  const DB_VER = 1;

  function idb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VER);
      req.onupgradeneeded = function () {
        const db = req.result;
        if (!db.objectStoreNames.contains("kv")) db.createObjectStore("kv");
        if (!db.objectStoreNames.contains("queue")) db.createObjectStore("queue", { keyPath: "client_uuid" });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  function idbGet(store, key) {
    return idb().then((db) => new Promise((resolve, reject) => {
      const r = db.transaction(store, "readonly").objectStore(store).get(key);
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    }));
  }
  function idbPut(store, val, key) {
    return idb().then((db) => new Promise((resolve, reject) => {
      const r = key !== undefined
        ? db.transaction(store, "readwrite").objectStore(store).put(val, key)
        : db.transaction(store, "readwrite").objectStore(store).put(val);
      r.onsuccess = () => resolve();
      r.onerror = () => reject(r.error);
    }));
  }
  function idbAll(store) {
    return idb().then((db) => new Promise((resolve, reject) => {
      const r = db.transaction(store, "readonly").objectStore(store).getAll();
      r.onsuccess = () => resolve(r.result || []);
      r.onerror = () => reject(r.error);
    }));
  }
  function idbClear(store) {
    return idb().then((db) => new Promise((resolve, reject) => {
      const r = db.transaction(store, "readwrite").objectStore(store).clear();
      r.onsuccess = () => resolve();
      r.onerror = () => reject(r.error);
    }));
  }

  function uuid() {
    if (crypto.randomUUID) return crypto.randomUUID();
    const b = new Uint8Array(16);
    crypto.getRandomValues(b);
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    const h = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
    return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
  }

  function banner(text, ok) {
    const el = document.getElementById("offline-banner");
    if (!el) return;
    if (!text) { el.hidden = true; el.textContent = ""; return; }
    el.hidden = false;
    el.textContent = text;
    el.classList.toggle("ok", !!ok);
  }

  function markNeedsNet(offline) {
    const sel = 'a[href*="/homework"],a[href*="/ai/teach"],a[href*="/parent"],[data-ai-ask]';
    document.querySelectorAll(sel).forEach((n) => n.classList.toggle("needs-net", offline));
  }

  function setOnlineUI() {
    const off = typeof navigator !== "undefined" && !navigator.onLine;
    markNeedsNet(off);
    if (off) banner("Учимся без интернета");
    else banner("");
  }

  function checkOffline(type, answerSpec, given) {
    const a = answerSpec || {};
    const g = given || {};
    const norm = (s) => String(s == null ? "" : s).trim().toLowerCase().replace(/ё/g, "е");
    switch (type) {
      case "single_choice":
      case "fill_blank_choice":
      case "audio_text_choice":
        return String(g.id || g.value || "") === String(a.id || a.value || a.correct || "");
      case "number_input":
      case "equation":
        return Number(g.value) === Number(a.value);
      case "text_input":
      case "dictation":
        return norm(g.value) === norm(a.value);
      case "fraction_input":
        return Number(g.num) === Number(a.num) && Number(g.den) === Number(a.den);
      case "fill_letters":
        return String(g.id || g.value || "") === String(a.id || a.value || a.letter || "");
      case "punctuation":
        return JSON.stringify([].concat(g.commas || []).map(Number).sort()) === JSON.stringify([].concat(a.commas || a.value || []).map(Number).sort());
      case "matching":
      case "drag_order":
      case "categorize":
      case "letter_tiles":
      case "tiles":
      case "step_by_step":
      case "morphemes":
        return JSON.stringify(g) === JSON.stringify(a) || JSON.stringify(g.value || g) === JSON.stringify(a.value || a);
      default:
        return JSON.stringify(g) === JSON.stringify(a);
    }
  }

  async function handleOfflineCheck(path, params, target) {
    const pkg = await idbGet("kv", "package");
    const m = path.match(/\/play\/(\d+)\/(?:ex|word)\/(\d+)\/check\//);
    const given = params.answer ? JSON.parse(params.answer) : {};
    let correct = false, isFinal = false;
    let item = { type: "ex" };
    if (pkg && m && path.indexOf("/ex/") !== -1) {
      item = (pkg.exercises || {})[m[2]] || {};
      correct = checkOffline(item.type, item.answer, given);
    } else if (pkg && m && path.indexOf("/word/") !== -1) {
      item = (pkg.words || {})[m[2]] || {};
      const expect = item.word || item.translation_ru || "";
      correct = String(given.value || given.en || given.ru || "").trim().toLowerCase() === String(expect).trim().toLowerCase()
        || String(given.value || "").trim().toLowerCase() === String(item.translation_ru || "").trim().toLowerCase();
    }
    const attemptNo = Number(params.attempt_no || 1);
    isFinal = correct || attemptNo >= 3 || params.show_solution === "1";
    const rec = {
      client_uuid: uuid(),
      client_created_at: new Date().toISOString(),
      block_id: m ? Number(m[1]) : null,
      exercise_id: path.indexOf("/ex/") !== -1 && m ? Number(m[2]) : null,
      word_id: path.indexOf("/word/") !== -1 && m ? Number(m[2]) : null,
      word_mode: params.mode || "",
      answer: given,
      attempt_no: attemptNo,
      hints_used: Number(params.hints_used || 0),
      duration_ms: Number(params.duration_ms || 0),
      solution_shown: params.show_solution === "1",
      client_correct: correct,
      client_final: isFinal,
      context: "mission",
    };
    await idbPut("queue", rec);
    const phrase = correct ? (attemptNo === 1 ? "Молодец!" : "Получилось!") : (isFinal ? "Разберём вместе в следующий раз." : "Почти! Попробуй ещё раз.");
    const html = `<div class="fb ${correct ? "ok" : "almost"}" data-final="${isFinal ? "1" : "0"}"><p>${phrase}</p>${isFinal ? `<p class="next"><a class="btn" href="/play/${m ? m[1] : ""}/">Дальше</a></p>` : ""}</div>`;
    const box = document.getElementById("feedback") || target;
    if (box) box.innerHTML = html;
    const ev = new CustomEvent("htmx:afterSwap", { bubbles: true, detail: { target: box, elt: box } });
    (box || document).dispatchEvent(ev);
  }

  async function flushQueue() {
    if (!navigator.onLine) return;
    const items = await idbAll("queue");
    if (!items.length) return;
    const token = document.body && document.body.dataset.csrf;
    try {
      const res = await fetch("/offline/sync/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": token || "" },
        credentials: "same-origin",
        body: JSON.stringify({ items }),
      });
      if (!res.ok) return;
      const data = await res.json();
      if (data.ok) {
        await idbClear("queue");
        banner("Всё сохранено ✓", true);
        setTimeout(() => { if (navigator.onLine) banner(""); }, 4000);
      }
    } catch (e) { /* останется в очереди */ }
  }

  async function downloadPackage() {
    if (!navigator.onLine || !document.body || !document.body.dataset.child) return;
    try {
      const res = await fetch("/offline/package/", { credentials: "same-origin" });
      if (!res.ok) return;
      const pkg = await res.json();
      await idbPut("kv", pkg, "package");
      const urls = [];
      (pkg.days || []).forEach((d) => (d.blocks || []).forEach((b) => { if (b.play_url) urls.push(b.play_url); }));
      (pkg.assets || []).forEach((u) => urls.push(u));
      if (navigator.serviceWorker && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: "cache-urls", urls });
      }
    } catch (e) { /* нет сети или не ребёнок */ }
  }

  async function clearOffline() {
    try {
      await idbClear("kv");
      await idbClear("queue");
      if (window.caches) {
        const keys = await caches.keys();
        await Promise.all(keys.filter((k) => k.indexOf("masya-") === 0).map((k) => caches.delete(k)));
      }
    } catch (e) { /* */ }
  }

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {});
    navigator.serviceWorker.addEventListener("message", (e) => {
      if (e.data && e.data.type === "sync") flushQueue();
    });
  }
  window.addEventListener("online", () => { setOnlineUI(); flushQueue(); });
  window.addEventListener("offline", setOnlineUI);
  document.addEventListener("DOMContentLoaded", function () {
    setOnlineUI();
    downloadPackage();
    flushQueue();
    if (navigator.serviceWorker && "sync" in window.ServiceWorkerRegistration.prototype) {
      navigator.serviceWorker.ready.then((reg) => { try { reg.sync.register("masya-sync"); } catch (e) {} });
    }
    document.querySelectorAll('form[action*="logout"]').forEach((f) => {
      f.addEventListener("submit", () => { clearOffline(); });
    });
  });

  document.addEventListener("htmx:beforeRequest", function (e) {
    const cfg = e.detail || {};
    const path = (cfg.path || (cfg.requestConfig && cfg.requestConfig.path) || "").split("?")[0];
    if (navigator.onLine) return;
    if (/\/(homework|ai)\//.test(path) || path.indexOf("/parent/") === 0) {
      e.preventDefault();
      banner("Нужен интернет");
      return;
    }
    if (path.indexOf("/check/") !== -1) {
      e.preventDefault();
      const params = (cfg.requestConfig && cfg.requestConfig.parameters) || cfg.parameters || {};
      handleOfflineCheck(path, params, cfg.target).catch(() => {});
    }
  });

  window.MasyaPWA = { flushQueue, downloadPackage, clearOffline, checkOffline };
})();
