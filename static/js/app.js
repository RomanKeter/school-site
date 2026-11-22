/* Учебный сайт — клиентская логика (без inline-скриптов: CSP) */
(function () {
  "use strict";

  // ---------- Озвучка (browser speechSynthesis) ----------
  function speak(text, lang) {
    if (!("speechSynthesis" in window) || !text) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang || document.body.dataset.enVariant || "en-GB";
    u.rate = 0.9;
    const voices = window.speechSynthesis.getVoices();
    const v = voices.find((x) => x.lang === u.lang) || voices.find((x) => x.lang.startsWith(u.lang.slice(0, 2)));
    if (v) u.voice = v;
    window.speechSynthesis.speak(u);
  }
  window.zSpeak = speak;

  document.addEventListener("click", function (e) {
    const sp = e.target.closest("[data-speak]");
    if (sp) { e.preventDefault(); speak(sp.dataset.speak, sp.dataset.lang); }
  });

  // ---------- Картинный пароль ----------
  function initPictures() {
    const form = document.getElementById("pwform");
    if (!form) return;
    const seq = [];
    const dots = form.querySelectorAll(".pwdots span");
    const hidden = form.querySelector("input[name=sequence]");
    function render() { dots.forEach((d, i) => (d.textContent = i < seq.length ? "●" : "○")); }
    form.querySelectorAll("[data-pic]").forEach((b) =>
      b.addEventListener("click", function () {
        if (seq.length >= 4) return;
        seq.push(b.dataset.pic);
        render();
        if (seq.length === 4) { hidden.value = seq.join(","); form.submit(); }
      })
    );
    const erase = form.querySelector("[data-erase]");
    if (erase) erase.addEventListener("click", function () { seq.pop(); render(); });
    render();
  }

  // ---------- Плеер задания ----------
  function initTask(root) {
    const form = root.querySelector("form.taskform");
    if (!form || form.dataset.ready) return;
    form.dataset.ready = "1";
    form.dataset.started = String(Date.now());
    const type = form.dataset.type;

    // выбор варианта: тап — сразу проверка
    form.querySelectorAll("[data-choice]").forEach((b) =>
      b.addEventListener("click", function (e) {
        e.preventDefault();
        if (form.dataset.final) return;
        form.querySelectorAll("[data-choice]").forEach((x) => x.classList.remove("sel"));
        b.classList.add("sel");
        form.dataset.choice = b.dataset.choice;
        htmx.trigger(form, "submit");
      })
    );

    // экранная клавиатура
    let focused = form.querySelector(".bigin");
    form.querySelectorAll(".bigin").forEach((i) => i.addEventListener("focus", () => (focused = i)));
    form.querySelectorAll("[data-key]").forEach((k) =>
      k.addEventListener("click", function (e) {
        e.preventDefault();
        if (!focused) return;
        const key = k.dataset.key;
        if (key === "back") focused.value = focused.value.slice(0, -1);
        else if (key === "next") {
          const all = Array.from(form.querySelectorAll(".bigin"));
          const i = all.indexOf(focused);
          if (all[i + 1]) { all[i + 1].focus(); focused = all[i + 1]; }
        } else focused.value += key;
      })
    );

    // соедини пары
    if (type === "matching") {
      let left = null, n = 0;
      const pairs = {};
      form.querySelectorAll("[data-left]").forEach((b) =>
        b.addEventListener("click", (e) => { e.preventDefault(); form.querySelectorAll("[data-left]").forEach((x) => x.classList.remove("sel")); b.classList.add("sel"); left = b; })
      );
      form.querySelectorAll("[data-right]").forEach((b) =>
        b.addEventListener("click", (e) => {
          e.preventDefault();
          if (!left) return;
          // убрать старую пару
          const old = Object.entries(pairs).find(([, r]) => r === b.dataset.right);
          if (old) { delete pairs[old[0]]; }
          const cls = "p" + (n++ % 5);
          [left, b].forEach((x) => { x.className = x.className.replace(/\bp\d\b/g, "").trim(); x.classList.add(cls); x.classList.remove("sel"); });
          pairs[left.dataset.left] = b.dataset.right;
          form.dataset.pairs = JSON.stringify(pairs);
          left = null;
        })
      );
    }

    // упорядочить: кнопки ↑↓ + перетаскивание
    if (type === "drag_order") {
      const list = form.querySelector(".order-list");
      list.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-move]");
        if (!btn) return;
        e.preventDefault();
        const li = btn.closest("li");
        if (btn.dataset.move === "up" && li.previousElementSibling) list.insertBefore(li, li.previousElementSibling);
        if (btn.dataset.move === "down" && li.nextElementSibling) list.insertBefore(li.nextElementSibling, li);
      });
      let dragged = null;
      list.querySelectorAll("li").forEach((li) => {
        li.draggable = true;
        li.addEventListener("dragstart", () => (dragged = li));
        li.addEventListener("dragover", (e) => e.preventDefault());
        li.addEventListener("drop", (e) => { e.preventDefault(); if (dragged && dragged !== li) list.insertBefore(dragged, li); });
      });
    }

    // корзины
    form.querySelectorAll("[data-bucket]").forEach((b) =>
      b.addEventListener("click", (e) => {
        e.preventDefault();
        b.closest(".cat-row").querySelectorAll("[data-bucket]").forEach((x) => x.classList.remove("sel"));
        b.classList.add("sel");
      })
    );

    // плитки букв
    if (type === "letter_tiles" || form.dataset.mode === "tiles") {
      const out = form.querySelector(".built");
      const used = [];
      form.querySelectorAll("[data-letter]").forEach((b) =>
        b.addEventListener("click", (e) => { e.preventDefault(); out.textContent += b.dataset.letter; b.disabled = true; used.push(b); })
      );
      form.addEventListener("tiles-reset", () => (used.length = 0));
      const back = form.querySelector("[data-tiles-back]");
      if (back) back.addEventListener("click", (e) => { e.preventDefault(); const b = used.pop(); if (b) { b.disabled = false; out.textContent = out.textContent.slice(0, -1); } });
    }

    // русский язык (D-203): буква встаёт в пропуск; запятые включаются тапом между словами
    if (type === "fill_letters") {
      const gap = form.querySelector(".gap");
      form.querySelectorAll("[data-choice]").forEach((b) => b.addEventListener("click", () => { if (gap) gap.textContent = b.dataset.choice === "0" ? "·" : b.textContent; }));
    }
    // разбор по составу (D-207): инструмент-морфема + тап по буквам; повторный тап тем же — стереть
    if (type === "morphemes") {
      let tool = "k";
      form.querySelectorAll("[data-tool]").forEach((t) => t.addEventListener("click", (e) => {
        e.preventDefault(); tool = t.dataset.tool;
        form.querySelectorAll("[data-tool]").forEach((x) => x.classList.toggle("sel", x === t));
      }));
      form.querySelectorAll(".mletter").forEach((b) => b.addEventListener("click", (e) => {
        e.preventDefault();
        b.dataset.m = (b.dataset.m || "") === tool ? "" : tool;
        b.className = "mletter" + (b.dataset.m ? " m-" + b.dataset.m : "");
      }));
      const z = form.querySelector("[data-zero]");
      if (z) z.addEventListener("click", (e) => { e.preventDefault(); z.classList.toggle("on"); z.setAttribute("aria-pressed", z.classList.contains("on")); });
    }
    // диктант (D-208): озвучка ru-RU, обычная и медленная
    if (type === "dictation") {
      form.querySelectorAll("[data-dict-play]").forEach((b) => b.addEventListener("click", (e) => {
        e.preventDefault();
        if (!("speechSynthesis" in window)) return;
        const bytes = Uint8Array.from(atob(b.dataset.say || ""), (c) => c.charCodeAt(0));
        const u = new SpeechSynthesisUtterance(new TextDecoder().decode(bytes));
        u.lang = "ru-RU"; u.rate = b.dataset.slow ? 0.55 : 0.85;
        const v = window.speechSynthesis.getVoices().find((x) => x.lang.startsWith("ru"));
        if (v) u.voice = v;
        window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);
      }));
    }
    if (type === "punctuation") {
      form.querySelectorAll("[data-gap]").forEach((b) =>
        b.addEventListener("click", (e) => { e.preventDefault(); b.classList.toggle("on"); b.setAttribute("aria-pressed", b.classList.contains("on")); })
      );
    }

    if (form.dataset.autospeak) setTimeout(() => speak(form.dataset.autospeak), 400);
  }

  function collect(form) {
    const type = form.dataset.type;
    const val = (sel) => (form.querySelector(sel) || {}).value || "";
    switch (type) {
      case "single_choice": case "fill_blank_choice": case "audio_text_choice": case "picture_choice": case "en_to_ru":
        return form.dataset.choiceKind === "value" ? { value: form.dataset.choice || "" } : { id: form.dataset.choice || "" };
      case "number_input": case "equation": case "text_input": case "ru_to_en":
        return { value: val("input[name=value]") };
      case "fraction_input":
        return { num: val("input[name=num]"), den: val("input[name=den]") };
      case "matching":
        return { pairs: JSON.parse(form.dataset.pairs || "{}") };
      case "drag_order":
        return { order: Array.from(form.querySelectorAll(".order-list li")).map((li) => li.dataset.id) };
      case "categorize": {
        const buckets = {};
        form.querySelectorAll(".cat-row").forEach((row) => {
          const sel = row.querySelector("[data-bucket].sel");
          if (sel) (buckets[sel.dataset.bucket] = buckets[sel.dataset.bucket] || []).push(row.dataset.item);
        });
        return { buckets: buckets };
      }
      case "fill_letters":
        return { id: form.dataset.choice || "" };
      case "morphemes":
        return { labels: Array.from(form.querySelectorAll(".mletter")).map((l) => l.dataset.m || "-").join(""),
                 zero: !!form.querySelector("[data-zero].on") };
      case "dictation":
        return { value: val("textarea[name=value]") };
      case "punctuation":
        return { commas: Array.from(form.querySelectorAll("[data-gap].on")).map((b) => Number(b.dataset.gap)) };
      case "letter_tiles": case "tiles":
        return { value: (form.querySelector(".built") || {}).textContent || "" };
      case "step_by_step":
        return { steps: Array.from(form.querySelectorAll("input[name=step]")).map((i) => i.value) };
      default:
        return {};
    }
  }

  document.addEventListener("htmx:configRequest", function (e) {
    const form = e.detail.elt.closest ? e.detail.elt.closest("form.taskform") : null;
    const tf = form || document.querySelector("form.taskform");
    if (!tf) return;
    const p = e.detail.parameters;
    p.attempt_no = tf.dataset.attempt || "1";
    p.hints_used = tf.dataset.hints || "0";
    p.mode = tf.dataset.mode || "";
    if (e.detail.path.indexOf("/check/") !== -1) {
      p.answer = JSON.stringify(collect(tf));
      p.duration_ms = String(Date.now() - Number(tf.dataset.started || Date.now()));
      if (e.detail.elt.dataset && e.detail.elt.dataset.solution) p.show_solution = "1";
    }
  });

  document.addEventListener("htmx:afterSwap", function (e) {
    const tf = document.querySelector("form.taskform");
    if (!tf) return;
    const t = e.detail.target;
    if (t.id === "hint-panel") {
      tf.dataset.hints = String(Number(tf.dataset.hints || 0) + 1);
      return;
    }
    if (t.id === "feedback") {
      const fb = t.querySelector(".fb");
      if (!fb) return;
      if (fb.dataset.final === "1") {
        tf.dataset.final = "1";
        tf.querySelectorAll("button, input").forEach((x) => (x.disabled = true));
        const ok = tf.querySelector("[data-choice].sel");
        if (ok && fb.classList.contains("ok")) ok.classList.add("ok");
        const actions = document.querySelector(".task-actions");
        if (actions) actions.hidden = true;
        const nx = t.querySelector(".next");
        if (nx) nx.focus();
      } else {
        tf.dataset.attempt = String(Number(tf.dataset.attempt || 1) + 1);
        tf.dataset.choice = "";
        tf.querySelectorAll("[data-choice].sel").forEach((x) => x.classList.remove("sel"));
        // плитки букв: после «почти» начинаем собирать слово заново
        const built = tf.querySelector(".built");
        if (built) { built.textContent = ""; tf.querySelectorAll("[data-letter]").forEach((b) => (b.disabled = false)); tf.dispatchEvent(new Event("tiles-reset")); }
        const sol = document.querySelector("[data-solution]");
        if (sol) sol.hidden = false;
        if (fb.dataset.autohint === "1") {
          const hb = document.querySelector("[data-hint-btn]");
          if (hb && Number(tf.dataset.hints || 0) === 0) htmx.trigger(hb, "click");
        }
      }
    }
  });

  // ---------- Разобранный пример: шаги по кнопке «Дальше» (DS-8) ----------
  function initWorked() {
    const box = document.getElementById("worked");
    if (!box) return;
    const steps = box.querySelectorAll(".wstep");
    const more = document.getElementById("worked-more");
    const go = document.getElementById("worked-go");
    let i = 0;
    steps.forEach((s, k) => (s.hidden = k > 0));
    function upd() { if (i >= steps.length - 1) { more.hidden = true; go.hidden = false; } }
    upd();
    more.addEventListener("click", () => { i++; if (steps[i]) steps[i].hidden = false; upd(); });
  }

  // ---------- Перерыв: «Продолжить» через 60 с ----------
  function initBreak() {
    const btn = document.getElementById("break-continue");
    if (!btn) return;
    let left = Number(btn.dataset.left || 60);
    const lbl = document.getElementById("break-left");
    const t = setInterval(() => {
      left--; if (lbl) lbl.textContent = String(Math.max(0, left));
      if (left <= 0) { clearInterval(t); btn.removeAttribute("disabled"); btn.classList.remove("secondary"); }
    }, 1000);
  }

  // ---------- Активное время (пинг каждые 30 с, если было действие за 60 с) ----------
  function initActivity() {
    if (!document.body.dataset.child || !document.querySelector("form.taskform, #worked")) return;
    let last = Date.now();
    ["click", "keydown", "touchstart"].forEach((ev) => document.addEventListener(ev, () => (last = Date.now()), { passive: true }));
    setInterval(function () {
      if (Date.now() - last > 60000) return;
      const token = document.body.dataset.csrf;
      fetch("/activity/ping/", { method: "POST", headers: { "X-CSRFToken": token }, credentials: "same-origin" })
        .then((r) => r.json()).then((d) => {
          const tf = document.querySelector("form.taskform");
          if (d.redirect && !(tf && !tf.dataset.final && tf.dataset.attempt > 1)) window.location = d.redirect;
        }).catch(() => {});
    }, 30000);
  }

  function initAll(root) {
    initTask(root || document);
  }

  document.addEventListener("DOMContentLoaded", function () {
    initPictures(); initAll(document); initWorked(); initBreak(); initActivity();
  });
  document.addEventListener("htmx:load", (e) => initAll(e.detail.elt));
})();
document.addEventListener("click", function (e) {
  const b = e.target.closest("[data-submit-task]");
  if (!b) return;
  e.preventDefault();
  const f = document.querySelector("form.taskform");
  if (f && !f.dataset.final) htmx.trigger(f, "submit");
});

// Стиль 2 (D-039): если SVG-картинки для значения нет — показываем прежний эмодзи из данных
(function () {
  function fallback(img) {
    if (!img || img.tagName !== "IMG" || img.dataset.fallback === undefined) return;
    const s = document.createElement("span");
    s.className = "emoji-fallback";
    s.textContent = img.dataset.fallback;
    img.replaceWith(s);
  }
  document.addEventListener("error", (e) => fallback(e.target), true);
  document.querySelectorAll("img[data-fallback]").forEach((img) => { if (img.complete && img.naturalWidth === 0) fallback(img); });
})();
