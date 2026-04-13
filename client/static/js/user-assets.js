/**
 * client/static/js/user-assets.js
 * Casual D&D — User asset upload + stat persistence helpers.
 *
 * Exposes a global `UserAssets` object.
 */
(function (global) {
  'use strict';

  /**
   * Upload a token or power-icon image to the current user's account.
   * @param {File} file
   * @param {'token'|'power_icon'} assetType
   * @returns {Promise<{ok, asset_id, url}>}
   */
  async function uploadAsset(file, assetType) {
    var formData = new FormData();
    formData.append('file', file);
    formData.append('asset_type', assetType || 'token');
    try {
      var res = await fetch('/api/users/me/assets/upload', {
        method: 'POST',
        credentials: 'same-origin',
        body: formData,
      });
      var data = await res.json();
      return { ok: res.ok, ...data };
    } catch (err) {
      return { ok: false, detail: 'Network error' };
    }
  }

  /**
   * Fetch all assets belonging to the current user.
   * @returns {Promise<Array>}
   */
  async function fetchMyAssets() {
    try {
      var res = await fetch('/api/users/me/assets', { credentials: 'same-origin' });
      if (!res.ok) return [];
      var data = await res.json();
      return data.assets || [];
    } catch (_) {
      return [];
    }
  }

  /**
   * Fetch the current user's character stats.
   * @returns {Promise<object|null>}
   */
  async function fetchMyStats() {
    try {
      var res = await fetch('/api/users/me/stats', { credentials: 'same-origin' });
      if (!res.ok) return null;
      var data = await res.json();
      return data.stats || null;
    } catch (_) {
      return null;
    }
  }

  /**
   * Persist character stat changes to the server.
   * @param {object} stats - partial or full stats object
   *   Keys: str, dex, con, int_, wis, cha, hp, max_hp, ac, speed
   * @returns {Promise<{ok, stats}>}
   */
  async function saveMyStats(stats) {
    try {
      var res = await fetch('/api/users/me/stats', {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(stats),
      });
      var data = await res.json();
      return { ok: res.ok, ...data };
    } catch (err) {
      return { ok: false, detail: 'Network error' };
    }
  }

  /**
   * Wire an existing <input type="file"> element to upload to the user's account
   * instead of session-local storage.
   *
   * Usage:
   *   UserAssets.wireTokenUpload(document.getElementById('token-upload-input'));
   *
   * @param {HTMLInputElement} inputEl
   * @param {Function} [onSuccess] - called with the asset object on upload success
   */
  function wireTokenUpload(inputEl, onSuccess) {
    if (!inputEl) return;
    inputEl.addEventListener('change', async function () {
      var file = inputEl.files && inputEl.files[0];
      if (!file) return;
      var result = await uploadAsset(file, 'token');
      if (result.ok && typeof onSuccess === 'function') {
        onSuccess(result);
      } else if (!result.ok) {
        var msg = result.detail || 'Upload failed';
        if (global.console) global.console.warn('[UserAssets] Upload error:', msg);
      }
      // Reset so the same file can be re-selected
      inputEl.value = '';
    });
  }

  global.UserAssets = {
    uploadAsset: uploadAsset,
    fetchMyAssets: fetchMyAssets,
    fetchMyStats: fetchMyStats,
    saveMyStats: saveMyStats,
    wireTokenUpload: wireTokenUpload,
  };

}(typeof window !== 'undefined' ? window : this));
