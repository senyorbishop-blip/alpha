/**
 * client/static/js/auth.js
 * Casual D&D — Auth API helper: login, register, logout, current user.
 *
 * Exposes a global `CasualAuth` object.
 */
(function (global) {
  'use strict';

  var _currentUser = null;
  var _nativeFetch = global.__casualNativeFetch || (global.fetch ? global.fetch.bind(global) : null);
  if (_nativeFetch && !global.__casualNativeFetch) global.__casualNativeFetch = _nativeFetch;

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

  function _sameOriginApiRequest(input) {
    try {
      var rawUrl = typeof input === 'string' ? input : (input && input.url) || '';
      if (!rawUrl) return false;
      var url = new URL(rawUrl, global.location && global.location.href ? global.location.href : undefined);
      return url.origin === global.location.origin && url.pathname.indexOf('/api/') === 0;
    } catch (_) {
      return false;
    }
  }

  function _authHeadersForFetch(input, init) {
    var sourceHeaders = (init && init.headers) || (input && input.headers) || {};
    var headers = new Headers(sourceHeaders);
    var token = getToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', 'Bearer ' + token);
    }
    return headers;
  }

  function apiFetch(input, init) {
    if (!_nativeFetch) return Promise.reject(new Error('fetch is unavailable'));
    if (!_sameOriginApiRequest(input)) return _nativeFetch(input, init);
    var nextInit = Object.assign({}, init || {});
    nextInit.headers = _authHeadersForFetch(input, init || {});
    if (!nextInit.credentials) nextInit.credentials = 'same-origin';
    return _nativeFetch(input, nextInit);
  }

  // Keep HTTP API auth in lockstep with the WebSocket auth path. The WS client
  // already sends sessionStorage.dnd_token as a query parameter; normal fetch()
  // calls used by character sheets/spells were cookie-only, which can fail after
  // reconnect/restart and produce 401s while the socket still works.
  if (_nativeFetch && !global.__casualAuthFetchPatched) {
    global.__casualAuthFetchPatched = true;
    global.fetch = function casualAuthFetch(input, init) {
      return apiFetch(input, init);
    };
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
      if (data.token || data.access_token || data.jwt) setToken(data.token || data.access_token || data.jwt);
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
    if (res.ok) {
      _currentUser = data.user || null;
      if (data.token || data.access_token || data.jwt) setToken(data.token || data.access_token || data.jwt);
    }
    return { ok: res.ok, ...data };
  }

  /**
   * Log out the current user.
   */
  async function logout() {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin', headers: _csrfHeaders() });
    _currentUser = null;
    if (global.sessionStorage) global.sessionStorage.removeItem('dnd_token');
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
   * Store the token returned by login/register for WS and fetch() API use.
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
    apiFetch: apiFetch,
  };

}(typeof window !== 'undefined' ? window : this));
