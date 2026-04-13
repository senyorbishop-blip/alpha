(function (global) {
  'use strict';

  const _SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

  /** Read the CSRF token from the cookie the server sets on GET responses. */
  function getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  async function requestJson(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    if (!_SAFE_METHODS.has(method)) {
      const token = getCsrfToken();
      if (token) {
        options = {
          ...options,
          headers: { 'X-CSRF-Token': token, ...(options.headers || {}) },
        };
      }
    }
    const response = await fetch(url, options);
    const contentType = response.headers.get('content-type') || '';
    const rawText = await response.text();
    let data = {};
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch (error) {
      console.error('[AppAPI] non-JSON response', { url, status: response.status, contentType, bodySnippet: rawText.slice(0, 240) });
      data = { ok: false, error: `Unexpected server response (${response.status}).` };
    }
    if (!response.ok || data.ok === false) {
      console.error('[AppAPI] request failed', { url, status: response.status, contentType, bodySnippet: rawText.slice(0, 240), data });
    }
    return { response, data, contentType, rawText };
  }

  async function fetchSessionInvites(sessionId, userId) {
    const { data } = await requestJson(`/api/session/${sessionId}/invites?user_id=${encodeURIComponent(userId)}`);
    return data;
  }

  async function uploadTokenImage(sessionId, userId, tokenId, file) {
    const fd = new FormData();
    fd.append('file', file);
    const { response, data } = await requestJson(`/api/session/${sessionId}/token/${tokenId}/image?user_id=${encodeURIComponent(userId)}`, { method: 'POST', body: fd });
    if (!response.ok || !data.ok) throw new Error(data.error || 'Token image upload failed.');
    return data;
  }

  async function createBlankPoiMap(sessionId, userId, poiId, cols, rows) {
    const { data } = await requestJson(`/api/session/${sessionId}/poi/${poiId}/blank_map?user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cols, rows }),
    });
    return data;
  }

  async function uploadPoiMapFile(sessionId, userId, poiId, file) {
    const fd = new FormData();
    fd.append('file', file);
    const { data } = await requestJson(`/api/session/${sessionId}/poi/${poiId}/map?user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
      body: fd,
    });
    return data;
  }

  async function uploadWorldMap(sessionId, userId, file, worldX, worldY) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('world_x', String(worldX));
    fd.append('world_y', String(worldY));
    const { data } = await requestJson(`/api/session/${sessionId}/map?user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
      body: fd,
    });
    return data;
  }

  async function clearWorldMaps(sessionId, userId) {
    const { data } = await requestJson(`/api/session/${sessionId}/map`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    return data;
  }

  global.AppAPI = {
    getCsrfToken,
    requestJson,
    fetchSessionInvites,
    uploadTokenImage,
    createBlankPoiMap,
    uploadPoiMapFile,
    uploadWorldMap,
    clearWorldMaps,
  };
})(window);
