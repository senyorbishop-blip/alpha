/**
 * client/static/js/auth.js
 * Casual D&D — Auth API helper: login, register, logout, current user.
 *
 * Exposes a global `CasualAuth` object.
 */
(function (global) {
  'use strict';

  var _currentUser = null;

  /** Read the CSRF token cookie set by the server on GET responses. */
  function _getCsrfToken() {
    if (global.AppAPI && global.AppAPI.getCsrfToken) return global.AppAPI.getCsrfToken();
    var match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function _csrfHeaders(extra) {
    var token = _getCsrfToken();
    return token ? Object.assign({ 'X-CSRF-Token': token }, extra || {}) : (extra || {});
  }

  /**
   * Fetch the currently authenticated user from the server.
   * Resolves with the user object or null if not authenticated.
   */
  async function fetchCurrentUser() {
    try {
      var res = await fetch('/api/auth/me', { credentials: 'same-origin' });
      if (!res.ok) { _currentUser = null; return null; }
      var data = await res.json();
      _currentUser = data.user || null;
      return _currentUser;
    } catch (_) {
      _currentUser = null;
      return null;
    }
  }

  /**
   * Register a new account.
   * @param {string} username
   * @param {string} email
   * @param {string} password
   * @param {string} role  - 'dm' | 'player' | 'viewer'
   * @returns {Promise<{ok, user, migrated, migrated_campaigns}>}
   */
  async function register(username, email, password, role) {
    var res = await fetch('/api/auth/register', {
      method: 'POST',
      credentials: 'same-origin',
      headers: _csrfHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ username: username, email: email, password: password, role: role }),
    });
    var data = await res.json();
    if (res.ok || res.status === 201) {
      _currentUser = data.user || null;
    }
    return { ok: res.ok || res.status === 201, ...data };
  }

  /**
   * Login with username-or-email + password.
   * @param {string} identifier
   * @param {string} password
   * @returns {Promise<{ok, user}>}
   */
  async function login(identifier, password) {
    var res = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: _csrfHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ username_or_email: identifier, password: password }),
    });
    var data = await res.json();
    if (res.ok) { _currentUser = data.user || null; }
    return { ok: res.ok, ...data };
  }

  /**
   * Log out the current user.
   */
  async function logout() {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin', headers: _csrfHeaders() });
    _currentUser = null;
  }

  /**
   * Look up account by email (triggers host-notification).
   */
  async function findId(email) {
    var res = await fetch('/api/auth/find-id', {
      method: 'POST',
      credentials: 'same-origin',
      headers: _csrfHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ email: email }),
    });
    return res.json();
  }

  /**
   * Return the cached current user (null if not loaded yet).
   */
  function getCurrentUser() {
    return _currentUser;
  }

  /**
   * Return the JWT from the session cookie (for WebSocket auth).
   * Reads the dnd_session httpOnly cookie value if accessible.
   * Because httpOnly cookies are not readable from JS, we fall back to
   * a token stored in sessionStorage by the login/register flow.
   */
  function getToken() {
    return global.sessionStorage ? (global.sessionStorage.getItem('dnd_token') || '') : '';
  }

  /**
   * Store the token returned by login/register for WS use.
   */
  function setToken(token) {
    if (global.sessionStorage && token) {
      global.sessionStorage.setItem('dnd_token', token);
    }
  }

  global.CasualAuth = {
    fetchCurrentUser: fetchCurrentUser,
    register: register,
    login: login,
    logout: logout,
    findId: findId,
    getCurrentUser: getCurrentUser,
    getToken: getToken,
    setToken: setToken,
  };

}(typeof window !== 'undefined' ? window : this));
