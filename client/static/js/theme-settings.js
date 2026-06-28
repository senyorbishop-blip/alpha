/* ============================================================================
   Casual D&D — Theme Settings controller
   - Applies the saved theme/accent on load (call early, before paint ideally).
   - If the settings panel markup (partials/theme-settings.html) is on the page,
     it auto-wires the controls. If not, applying still works.
   - Persists to localStorage. Emits 'mf-theme-change' so your app can react
     to HUD size / position / show-hide if you choose to hook them.
   ============================================================================ */
(function () {
  "use strict";

  var ROOT = document.documentElement;
  var KEY = "casual-dnd-theme-settings-v1";

  var THEMES = [
    "dark-fantasy", "parchment", "arcane-cyan", "blood-steel",
    "wood-elves", "divine", "necromancer", "high-contrast"
  ];
  var THEME_ACCENT = {
    "dark-fantasy": "#00e5cc", "parchment": "#7a4e14", "arcane-cyan": "#22d3ee",
    "blood-steel": "#e3342f", "wood-elves": "#c9a24a", "divine": "#c8a13a",
    "necromancer": "#7fe08a", "high-contrast": "#ffd400"
  };

  var DEFAULTS = {
    theme: "dark-fantasy",
    accent: "auto",            // "auto" = use the theme's accent, or a hex string
    hudScale: "1",
    hudPosition: "left",
    reduceMotion: false,
    hubBorder: "none",
    show: { passive: true, speed: true, quest: true,
            initiative: false, conditions: false, discovery: false }
  };

  function load() {
    try {
      return Object.assign({}, DEFAULTS,
        JSON.parse(localStorage.getItem(KEY) || "{}"),
        { show: Object.assign({}, DEFAULTS.show,
            (JSON.parse(localStorage.getItem(KEY) || "{}").show) || {}) });
    } catch (e) { return JSON.parse(JSON.stringify(DEFAULTS)); }
  }
  function save(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} }

  function hexToSoft(hex) {
    var n = parseInt(hex.slice(1), 16);
    return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + ",0.18)";
  }
  function resolvedAccent(s) {
    return s.accent === "auto" ? (THEME_ACCENT[s.theme] || "#00e5cc") : s.accent;
  }

  var state = load();

  function apply() {
    var acc = resolvedAccent(state);
    ROOT.setAttribute("data-theme", state.theme);
    ROOT.setAttribute("data-reduce-motion", state.reduceMotion ? "true" : "false");
    ROOT.style.setProperty("--mf-accent", acc);
    ROOT.style.setProperty("--mf-accent-soft", hexToSoft(acc));
    // also bend the existing cyan accent so glows/role-player colour follow the picker
    ROOT.style.setProperty("--mf-cyan", acc);
    ROOT.style.setProperty("--mf-cyan-soft", hexToSoft(acc));
    ROOT.style.setProperty("--mf-hud-scale", state.hudScale);
    ROOT.setAttribute("data-hud-position", state.hudPosition);
    // hub border preset — applied to the player's own card element only
    var card = document.getElementById("mychar-card");
    if (card) {
      var border = state.hubBorder || "none";
      card.setAttribute("data-hub-border", border);
      if (border !== "none") { card.classList.add("mf-themed"); }
      else { card.classList.remove("mf-themed"); }
    }

    // let the rest of the app react to non-colour prefs if it wants to
    document.dispatchEvent(new CustomEvent("mf-theme-change", { detail: JSON.parse(JSON.stringify(state)) }));
    syncControls();
  }

  /* ---- optional panel wiring (no-ops if the panel isn't present) ---- */
  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $all(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }

  function syncControls() {
    var sel = $("[data-mf='theme']"); if (sel) sel.value = state.theme;
    var hb = $("[data-mf='hubBorder']"); if (hb) hb.value = state.hubBorder || "none";
    $all("[data-mf-size]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-mf-size") === state.hudScale)); });
    $all("[data-mf-pos]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-mf-pos") === state.hudPosition)); });
    $all("[data-mf-accent]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(state.accent !== "auto" && b.getAttribute("data-mf-accent") === state.accent)); });
    $all("[data-mf-show]").forEach(function (c) { c.checked = !!state.show[c.getAttribute("data-mf-show")]; });
    var r = $("[data-mf='reduce']"); if (r) r.setAttribute("aria-pressed", String(state.reduceMotion));
  }

  function wire() {
    var sel = $("[data-mf='theme']");
    if (sel) sel.addEventListener("change", function () { state.theme = sel.value; save(state); apply(); });
    var hb = $("[data-mf='hubBorder']");
    if (hb) hb.addEventListener("change", function () { state.hubBorder = hb.value; save(state); apply(); });

    $all("[data-mf-size]").forEach(function (b) {
      b.addEventListener("click", function () { state.hudScale = b.getAttribute("data-mf-size"); save(state); apply(); }); });
    $all("[data-mf-pos]").forEach(function (b) {
      b.addEventListener("click", function () { state.hudPosition = b.getAttribute("data-mf-pos"); save(state); apply(); }); });
    $all("[data-mf-accent]").forEach(function (b) {
      b.addEventListener("click", function () { state.accent = b.getAttribute("data-mf-accent"); save(state); apply(); }); });
    $all("[data-mf-show]").forEach(function (c) {
      c.addEventListener("change", function () { state.show[c.getAttribute("data-mf-show")] = c.checked; save(state); apply(); }); });
    var r = $("[data-mf='reduce']");
    if (r) r.addEventListener("click", function () { state.reduceMotion = !state.reduceMotion; save(state); apply(); });
    var reset = $("[data-mf='reset']");
    if (reset) reset.addEventListener("click", function () { state = JSON.parse(JSON.stringify(DEFAULTS)); save(state); apply(); });
  }

  // public API
  window.CasualThemes = {
    apply: apply,
    set: function (patch) { Object.assign(state, patch); save(state); apply(); },
    get: function () { return JSON.parse(JSON.stringify(state)); },
    themes: THEMES
  };

  // apply ASAP to avoid a flash, then wire controls once DOM is ready
  apply();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { wire(); syncControls(); });
  } else { wire(); syncControls(); }
})();
