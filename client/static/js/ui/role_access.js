(function (global) {
  'use strict';

  // Pure role/scope access helpers — no globals, no env object, no DOM.
  //
  // All functions take explicit (role, scopes, …) arguments so they are
  // trivially unit-testable and usable in both play.html and future modules.
  //
  // Relationship to tabs.js:
  //   tabs.js exposes env-based analogues (isRole, hasAssistantScope,
  //   canUsePlayerTabs, canUseDmLibraryTabs) that serve the same purpose
  //   inside AppUITabs.  Those are intentionally separate — they depend on
  //   the env contract, not on raw role strings.  This module is the
  //   canonical home for the raw-param versions used by play.html.
  //
  // Load-order contract:
  //   This script must be loaded before the play.html inline <script> block
  //   so that window.RoleAccessHelpers is available when the wrapper
  //   functions (__hasAssistantScope, __canAccessDmControl, __canUseFlyout)
  //   are first called.  The wrappers carry inline fallback implementations
  //   for safety in case load order ever regresses.

  // ---------------------------------------------------------------------------
  // Flyout scope map
  // ---------------------------------------------------------------------------

  // Maps flyout panel element IDs to the assistant_dm scope string required
  // to open them.  An empty string means "dm-only, no scope delegation".
  // undefined (i.e. key absent) means the flyout is unrestricted.
  //
  // CANONICAL SOURCE: edit this map when adding or changing flyout permissions.
  // The inline copy in play.html's __ROLE_FLYOUT_SCOPE is a load-order
  // fallback only — do not add entries there.
  const FLYOUT_SCOPE_MAP = {
    'flyout-token':     '',
    'flyout-map':       '',
    'flyout-perm':      '',
    'flyout-editor':    '',
    'flyout-cart':      '',
    'flyout-assistant': '',
    'flyout-fog':       'maps.fog',
    'flyout-sound':     'narration.broadcast',
  };

  // ---------------------------------------------------------------------------
  // Pure helpers
  // ---------------------------------------------------------------------------

  /**
   * Build a normalized Set of assistant DM permission scopes from a raw array.
   *
   * @param {string[]|null|undefined} scopes - raw scope strings
   * @returns {Set<string>}
   */
  function buildScopeSet(scopes) {
    return new Set(
      (Array.isArray(scopes) ? scopes : [])
        .map((v) => String(v || '').trim())
        .filter(Boolean)
    );
  }

  /**
   * Return true when a participant with the given role has the specified
   * assistant DM scope.  Always false for any role other than 'assistant_dm'.
   *
   * @param {string} role
   * @param {string[]|null|undefined} scopes - raw scope array
   * @param {string} scope
   * @returns {boolean}
   */
  function hasScope(role, scopes, scope) {
    if (String(role || '').toLowerCase() !== 'assistant_dm') return false;
    return buildScopeSet(scopes).has(String(scope || '').trim());
  }

  /**
   * Check whether a participant can access a DM control that requires a scope.
   *
   * - 'dm' role always passes.
   * - 'assistant_dm' passes only when requiredScope is non-empty and held.
   *   An empty requiredScope means "dm-only, no scope delegation" → blocked.
   * - All other roles are blocked.
   *
   * @param {string} role
   * @param {string[]|null|undefined} scopes - raw scope array
   * @param {string} requiredScope - empty string = dm-only (no delegation)
   * @returns {boolean}
   */
  function canAccessDmControl(role, scopes, requiredScope) {
    const r = String(role || '').toLowerCase();
    if (r === 'dm') return true;
    if (r !== 'assistant_dm') return false;
    const normalized = String(requiredScope || '').trim();
    return normalized ? hasScope(role, scopes, normalized) : false;
  }

  /**
   * Check whether a participant can open a named flyout panel.
   *
   * Flyout IDs not present in scopeMap default to allowed (public/unlisted
   * tools).  IDs in scopeMap are gated by canAccessDmControl.
   *
   * @param {string} id - flyout element id (e.g. 'flyout-fog')
   * @param {string} role
   * @param {string[]|null|undefined} scopes - raw scope array
   * @param {Object} [scopeMap] - override for FLYOUT_SCOPE_MAP (testing only)
   * @returns {boolean}
   */
  function canUseFlyout(id, role, scopes, scopeMap) {
    const map = scopeMap || FLYOUT_SCOPE_MAP;
    const flyoutId = String(id || '');
    const scope = map[flyoutId];
    if (scope === undefined) return true;
    return canAccessDmControl(role, scopes, scope);
  }

  // ---------------------------------------------------------------------------
  // Export
  // ---------------------------------------------------------------------------

  global.RoleAccessHelpers = {
    FLYOUT_SCOPE_MAP,
    buildScopeSet,
    hasScope,
    canAccessDmControl,
    canUseFlyout,
  };
})(window);
