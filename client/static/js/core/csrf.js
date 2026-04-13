/**
 * client/static/js/core/csrf.js
 *
 * Client-side CSRF protection — double-submit cookie pattern.
 *
 * The server sets a `csrf_token` cookie on every GET response (readable by
 * JavaScript because it is NOT HttpOnly).  This script patches `window.fetch`
 * so that every state-changing same-origin request (POST, PUT, PATCH, DELETE)
 * automatically echoes that token back in an `X-CSRF-Token` request header.
 *
 * Load this script as early as possible — before any other script that calls
 * `fetch` — so the patch is in place before any requests are made.
 */
(function (global) {
  'use strict';

  var _SAFE_METHODS = { GET: true, HEAD: true, OPTIONS: true };

  function getCsrfToken() {
    var match = global.document && global.document.cookie
      ? global.document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
      : null;
    return match ? decodeURIComponent(match[1]) : '';
  }

  var _originalFetch = global.fetch;
  if (!_originalFetch) return; // Non-browser environment — do nothing.

  global.fetch = function csrfFetch(resource, init) {
    var method = 'GET';
    if (init && init.method) {
      method = String(init.method).toUpperCase();
    } else if (resource && typeof resource === 'object' && resource.method) {
      method = String(resource.method).toUpperCase();
    }

    if (_SAFE_METHODS[method]) {
      return _originalFetch.call(global, resource, init);
    }

    // Only inject for same-origin requests.
    var url = (typeof resource === 'string') ? resource : (resource.url || '');
    var isSameOrigin = !url || url.startsWith('/') || url.startsWith(global.location.origin);
    if (!isSameOrigin) {
      return _originalFetch.call(global, resource, init);
    }

    var token = getCsrfToken();
    if (!token) {
      return _originalFetch.call(global, resource, init);
    }

    // Merge CSRF header without mutating the caller's headers object.
    var newInit = init ? Object.assign({}, init) : {};
    if (newInit.headers instanceof Headers) {
      var h = new Headers(newInit.headers);
      h.set('X-CSRF-Token', token);
      newInit.headers = h;
    } else if (newInit.headers && typeof newInit.headers === 'object') {
      newInit.headers = Object.assign({ 'X-CSRF-Token': token }, newInit.headers);
    } else {
      newInit.headers = { 'X-CSRF-Token': token };
    }

    return _originalFetch.call(global, resource, newInit);
  };

  // Expose helper so other modules can read the token without cookie-parsing.
  global.getCsrfToken = getCsrfToken;
})(window);
