/**
 * client/static/js/campaign-claim.js
 * Casual D&D — Campaign claiming UI logic.
 *
 * Handles:
 *  - Rendering the "Uncollected Campaigns" section with Claim buttons
 *  - PATCH /api/campaigns/{id}/claim call
 *  - WebSocket `campaign_claimed` event (removes card from shared pool)
 *  - Animate card from Uncollected → My Campaigns on success
 *  - 409 conflict toast
 *
 * Exposes a global `CampaignClaim` object.
 */
(function (global) {
  'use strict';

  /**
   * Claim a campaign by ID.
   * @param {string} campaignId
   * @returns {Promise<{ok: boolean, conflict: boolean, data: object}>}
   */
  async function claimCampaign(campaignId) {
    try {
      var res = await fetch('/api/campaigns/' + encodeURIComponent(campaignId) + '/claim', {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
      });
      var data = await res.json();
      return { ok: res.ok, conflict: res.status === 409, data: data };
    } catch (err) {
      return { ok: false, conflict: false, data: { detail: 'Network error' } };
    }
  }

  /**
   * Fetch unclaimed (shared-pool) campaigns.
   * @returns {Promise<Array>}
   */
  async function fetchUnclaimed() {
    try {
      var res = await fetch('/api/campaigns/unclaimed', { credentials: 'same-origin' });
      if (!res.ok) return [];
      var data = await res.json();
      return data.campaigns || [];
    } catch (_) {
      return [];
    }
  }

  /**
   * Fetch campaigns owned by the current user.
   * @returns {Promise<Array>}
   */
  async function fetchMyCampaigns() {
    try {
      var res = await fetch('/api/campaigns/mine', { credentials: 'same-origin' });
      if (!res.ok) return [];
      var data = await res.json();
      return data.campaigns || [];
    } catch (_) {
      return [];
    }
  }

  /**
   * Handle incoming WebSocket `campaign_claimed` event.
   * Removes the claimed campaign card from the Uncollected section.
   *
   * @param {object} payload  - { campaign_id, claimed_by }
   * @param {string} myUsername
   * @param {Function} onClaimedByMe - called when the local user's claim is confirmed via WS
   */
  function handleClaimedEvent(payload, myUsername, onClaimedByMe) {
    var cid = payload && payload.campaign_id;
    if (!cid) return;

    // Remove from uncollected list
    var card = global.document && global.document.querySelector(
      '[data-unclaimed-id="' + cid + '"]'
    );
    if (card) {
      card.style.transition = 'opacity 0.35s, transform 0.35s';
      card.style.opacity = '0';
      card.style.transform = 'translateX(30px)';
      setTimeout(function () { if (card.parentNode) card.parentNode.removeChild(card); }, 380);
    }

    if (payload.claimed_by === myUsername && typeof onClaimedByMe === 'function') {
      onClaimedByMe(cid);
    }
  }

  /**
   * Render a single unclaimed campaign card element.
   * @param {object} campaign
   * @param {Function} onClaim - called with campaignId when Claim is clicked
   * @returns {HTMLElement}
   */
  function renderUnclaimedCard(campaign, onClaim) {
    var doc = global.document;
    if (!doc) return null;

    var card = doc.createElement('div');
    card.className = 'campaign-card unclaimed-card';
    card.dataset.unclaimedId = campaign.id;

    var date = campaign.updated_at
      ? new Date(campaign.updated_at * 1000).toLocaleDateString()
      : '—';

    card.innerHTML =
      '<div class="campaign-card-info">' +
        '<span class="campaign-name">' + _esc(campaign.name) + '</span>' +
        '<span class="campaign-meta">DM: Unclaimed · Last saved: ' + _esc(date) + '</span>' +
      '</div>' +
      '<div class="campaign-card-actions">' +
        '<button class="campaign-btn btn-view">View</button>' +
        '<button class="campaign-btn btn-claim" title="Claim this campaign">Claim ⚑</button>' +
      '</div>';

    card.querySelector('.btn-claim').addEventListener('click', function () {
      if (typeof onClaim === 'function') onClaim(campaign.id, card);
    });

    card.querySelector('.btn-view').addEventListener('click', function () {
      // Load the campaign in read-only mode (delegates to existing resume logic)
      if (global._campaignResume) {
        global._campaignResume(campaign.id);
      }
    });

    return card;
  }

  /**
   * Animate a card moving into "My Campaigns" with a gold flash.
   * @param {HTMLElement} card
   * @param {HTMLElement} myContainer
   */
  function animateClaimSuccess(card, myContainer) {
    card.style.transition = 'background 0.3s, box-shadow 0.3s';
    card.style.background = 'rgba(212,166,55,0.18)';
    card.style.boxShadow = '0 0 16px rgba(212,166,55,0.5)';
    setTimeout(function () {
      card.style.transition = 'opacity 0.4s, transform 0.4s';
      card.style.opacity = '0';
      card.style.transform = 'translateY(-10px) scale(0.97)';
      setTimeout(function () {
        if (card.parentNode) card.parentNode.removeChild(card);
        // Trigger a refresh of My Campaigns section
        if (global.CampaignClaim && global.CampaignClaim.refreshMyCampaigns) {
          global.CampaignClaim.refreshMyCampaigns();
        }
      }, 420);
    }, 350);
  }

  function _esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  global.CampaignClaim = {
    claimCampaign: claimCampaign,
    fetchUnclaimed: fetchUnclaimed,
    fetchMyCampaigns: fetchMyCampaigns,
    handleClaimedEvent: handleClaimedEvent,
    renderUnclaimedCard: renderUnclaimedCard,
    animateClaimSuccess: animateClaimSuccess,
  };

}(typeof window !== 'undefined' ? window : this));
