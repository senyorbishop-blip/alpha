/**
 * shopkeeper_dialogue.js — flavor-only reactive shopkeeper speech for ShopView.
 */
(function () {
  'use strict';

  const PERSONALITIES = ['friendly', 'gruff', 'greedy', 'shifty', 'scholarly'];
  const EVENTS = ['greeting', 'purchase', 'haggle_win', 'haggle_fail', 'cannot_afford', 'sell_accepted', 'sell_rejected', 'farewell'];
  const SHOP_TYPES = ['general', 'blacksmith', 'alchemist', 'magic', 'black_market'];
  const FALLBACK_TYPE = 'general';
  const AI_GREETING_CACHE = new Map();

  const STYLE_ID = 'shopkeeper-dialogue-style';

  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function stableHash(str) {
    let h = 2166136261;
    const s = String(str || 'shop');
    for (let i = 0; i < s.length; i += 1) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function pickVariant(lines, seed, event) {
    if (!Array.isArray(lines) || !lines.length) return '';
    return lines[(stableHash(`${seed}:${event}`) % lines.length)];
  }

  const TYPE_NOUNS = {
    general: 'sundries',
    blacksmith: 'steel',
    alchemist: 'tonics',
    magic: 'arcana',
    black_market: 'discreet goods',
  };

  const EVENT_LINES = {
    friendly: {
      greeting: ['Welcome in, friend! The {type} are ready for you.', 'Take your time—good {type} reward patient eyes.', 'If you need a hand with the {type}, just ask.', 'The door is open and the {type} are warm.'],
      purchase: ['Wonderful choice from the {type}.', 'That should help nicely.', 'I hope it brings you luck.', 'Packed with care for you.'],
      haggle_win: ['You argue kindly. I can meet you there.', 'A fair point—discount granted.', 'For a pleasant customer, I can bend.', 'You have earned that better price.'],
      haggle_fail: ['I am sorry, but the price must stand.', 'I cannot go lower today.', 'That would leave me short, friend.', 'Not this time, I am afraid.'],
      cannot_afford: ['No shame in coming back later.', 'Your purse needs a little rest first.', 'I will keep the counter warm.', 'Coin and desire will meet eventually.'],
      sell_accepted: ['I can use that. Deal.', 'Fair enough, here is your coin.', 'That will find a good shelf.', 'Accepted with thanks.'],
      sell_rejected: ['Not for this counter, I am afraid.', 'I cannot use that today.', 'Try another merchant for that.', 'No thank you, friend.'],
      farewell: ['Safe roads to you.', 'Come back with coin and stories.', 'May your pack feel lighter.', 'Until the next bargain.'],
    },
    gruff: {
      greeting: ['Look sharp. The {type} are not toys.', 'Say what you need and mind the {type}.', 'Good {type}, fair prices, little chatter.', 'Browse quick. I have work to do.'],
      purchase: ['A sound choice.', 'Done. Next.', 'That will serve.', 'Keep it maintained.'],
      haggle_win: ['Fine. You made your point.', 'I can shave a little off.', 'Do not make me regret this.', 'Price bends once.'],
      haggle_fail: ['No. Price stands.', 'You done bargaining?', 'My counter is not a charity.', 'Move along if that is your offer.'],
      cannot_afford: ['Your purse is light.', 'No coin, no goods.', 'Come back funded.', 'I do not sell promises.'],
      sell_accepted: ['I can move that.', 'Deal.', 'It will do.', 'Coin for goods. Simple.'],
      sell_rejected: ['Not interested.', 'Wrong counter.', 'Keep it.', 'No deal.'],
      farewell: ['Mind the road.', 'Door is there.', 'Come back ready.', 'Hmph.'],
    },
    greedy: {
      greeting: ['Ah, a customer with coin for {type}.', 'Every shelf of {type} is an opportunity.', 'Quality {type} costs, and mine is quality.', 'Let us turn your purse into preparedness.'],
      purchase: ['Excellent investment—for both of us.', 'Your coin has excellent taste.', 'A profitable decision.', 'I do adore decisive customers.'],
      haggle_win: ['Painful, but profitable enough.', 'Fine, a modest concession.', 'You nibble my margin well.', 'I will allow this bargain.'],
      haggle_fail: ['Do not bruise my margins.', 'The price is already generous.', 'That offer insults the counter.', 'Try that again and the price rises.'],
      cannot_afford: ['Your purse is lighter than your ambition.', 'Come back when coin and desire agree.', 'I sell goods, not dreams.', 'No credit today.'],
      sell_accepted: ['I can profit from that.', 'A tidy acquisition.', 'Fine, here is your coin.', 'This will resell nicely.'],
      sell_rejected: ['No profit in that.', 'Dead stock. Pass.', 'I buy value, not clutter.', 'Not worth my shelf space.'],
      farewell: ['Return with heavier purses.', 'Spend wisely—preferably here.', 'May fortune fill your coin pouch.', 'The next deal awaits.'],
    },
    shifty: {
      greeting: ['Keep your voice low around the {type}.', 'Nothing here has a past worth mentioning.', 'You did not find me; I found you.', 'Coin first, questions never.'],
      purchase: ['You never got that here.', 'Pleasure, quietly.', 'Hide it before daylight.', 'Clean deal. No names.'],
      haggle_win: ['Sharp tongue. Fine.', 'Quietly, then. Less coin.', 'You know the game.', 'A risky discount, but yours.'],
      haggle_fail: ['Do not push in public.', 'Wrong whisper, wrong price.', 'That kind of talk costs extra.', 'The number stays.'],
      cannot_afford: ['Come back with real coin.', 'Dream quieter.', 'No credit. Too traceable.', 'Empty purses draw attention.'],
      sell_accepted: ['I can make that disappear.', 'Useful. Deal.', 'No questions asked.', 'It changes hands now.'],
      sell_rejected: ['Too visible. I pass.', 'Not touching that.', 'Wrong kind of risk.', 'Take that elsewhere.'],
      farewell: ['You were never here.', 'Watch the alleys.', 'Leave separately from your questions.', 'Fade out cleanly.'],
    },
    scholarly: {
      greeting: ['Do observe the {type} with care.', 'A discerning buyer honors provenance.', 'Please note each practical application.', 'Knowledge is priceless; these wares merely expensive.'],
      purchase: ['An empirically sound selection.', 'A practical acquisition.', 'May its properties prove useful.', 'I approve the choice.'],
      haggle_win: ['A compelling argument. Accepted.', 'Your reasoning has merit.', 'The arithmetic can accommodate that.', 'A persuasive thesis. Discount granted.'],
      haggle_fail: ['Your premise is unsupported.', 'The valuation remains unchanged.', 'A weak argument for a lower sum.', 'I reject the calculation.'],
      cannot_afford: ['The arithmetic is unfavorable.', 'Acquisition requires liquidity.', 'Return when funds support intent.', 'Desire alone cannot settle accounts.'],
      sell_accepted: ['Cataloguable. Accepted.', 'A useful specimen.', 'I can classify and resell it.', 'The valuation is acceptable.'],
      sell_rejected: ['Insufficient relevance.', 'It does not fit my catalog.', 'No scholarly demand for that.', 'Rejected on practical grounds.'],
      farewell: ['May your observations be precise.', 'Return with field notes.', 'Safe travels and sound reasoning.', 'Until our next transaction.'],
    },
  };

  const LINE_BANK = EVENTS.reduce((bank, event) => {
    bank[event] = {};
    PERSONALITIES.forEach((personality) => {
      bank[event][personality] = {};
      SHOP_TYPES.forEach((shopType) => {
        const noun = TYPE_NOUNS[shopType] || TYPE_NOUNS.general;
        bank[event][personality][shopType] = (EVENT_LINES[personality][event] || EVENT_LINES.friendly[event])
          .map(line => line.replace(/\{type\}/g, noun));
      });
    });
    return bank;
  }, {});

  function variants(event, personality, shopType) {
    return LINE_BANK[event]?.[personality]?.[shopType]
      || LINE_BANK[event]?.[personality]?.[FALLBACK_TYPE]
      || LINE_BANK.greeting.friendly.general;
  }

  function lineFor(event, ctx) {
    const personality = PERSONALITIES.includes(String(ctx?.personality || '').toLowerCase()) ? String(ctx.personality).toLowerCase() : 'friendly';
    const shopType = SHOP_TYPES.includes(String(ctx?.shop_type || ctx?.shopType || '').toLowerCase()) ? String(ctx.shop_type || ctx.shopType).toLowerCase() : FALLBACK_TYPE;
    if (event === 'greeting' && ctx?.greeting_override) return String(ctx.greeting_override).trim();
    return pickVariant(variants(event, personality, shopType), ctx?.shop_id || ctx?.shopId || ctx?.id || 'shop', event);
  }

  function ensureStyle() {
    if (typeof document === 'undefined' || document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `.shopkeeper-speech-strip{margin:.45rem 0 0;padding:.5rem .7rem;border-radius:10px;background:rgba(245,232,200,.14);border:1px solid rgba(245,200,90,.35);color:#fff3d0;font-size:13px;line-height:1.35;display:flex;gap:.5rem;align-items:flex-start}.shopkeeper-speech-strip .skd-text{flex:1}.shopkeeper-speech-strip .skd-dismiss{border:0;background:transparent;color:#f5e8c8;cursor:pointer;font-weight:800}`;
    document.head.appendChild(style);
  }

  function render(text, ctx) {
    if (typeof document === 'undefined' || !text) return text;
    if (ctx && ctx.dialogue_enabled === false) return text;
    const modal = document.getElementById('dnd-shop-view');
    if (!modal) return text;
    const headerLeft = modal.querySelector('.sv-header-left') || modal.querySelector('.sv-header');
    if (!headerLeft) return text;
    ensureStyle();
    let strip = modal.querySelector('.shopkeeper-speech-strip');
    if (!strip) {
      strip = document.createElement('div');
      strip.className = 'shopkeeper-speech-strip';
      strip.innerHTML = '<span class="skd-text"></span><button type="button" class="skd-dismiss" aria-label="Dismiss shopkeeper dialogue">×</button>';
      strip.querySelector('.skd-dismiss').addEventListener('click', () => strip.remove());
      headerLeft.appendChild(strip);
    }
    strip.querySelector('.skd-text').innerHTML = `“${esc(text)}”`;
    return text;
  }

  function say(event, ctx) {
    const normalizedEvent = EVENTS.includes(String(event || '')) ? String(event) : 'greeting';
    if (ctx && ctx.dialogue_enabled === false) return '';
    const text = lineFor(normalizedEvent, ctx || {});
    return render(text, ctx || {});
  }

  async function enrichGreeting(ctx) {
    if (!ctx || ctx.dialogue_enabled === false || ctx.ai_greeting === false) return null;
    const key = String(ctx.shop_id || ctx.id || 'shop');
    if (AI_GREETING_CACHE.has(key)) return AI_GREETING_CACHE.get(key);
    try {
      const statusResp = await fetch('/api/assistant/status');
      const status = await statusResp.json();
      if (!statusResp.ok || status.ok === false || status.available === false) return null;
      const body = {
        action: 'draft_npc_line',
        token_name: ctx.shopkeeper_name || 'Shopkeeper',
        token_notes: `${ctx.personality || 'friendly'} ${ctx.shop_type || 'general'} shopkeeper. ${ctx.description || ''}`.trim(),
        player_message: 'Greet customers entering the shop in one short in-character line.',
        campaign_tone: 'heroic',
      };
      const resp = await fetch('/api/assistant/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await resp.json();
      const text = String(data?.content?.text || data?.summary || '').split('\n').find(Boolean)?.trim().replace(/^"|"$/g, '');
      if (resp.ok && text) {
        AI_GREETING_CACHE.set(key, text.slice(0, 220));
        render(AI_GREETING_CACHE.get(key), ctx);
        return AI_GREETING_CACHE.get(key);
      }
    } catch (_err) { /* optional network enhancement only */ }
    return null;
  }

  function speakGreeting(text, ctx) {
    if (!text || !ctx || ctx.tts_enabled !== true) return;
    const voice = String(ctx.voice || '').trim() || 'grand_narrator';
    if (window.tavernTTS && typeof window.tavernTTS.speak === 'function') {
      window.tavernTTS.speak(text, voice, 'warm');
    }
  }

  window.ShopkeeperDialogue = { say, lineFor, enrichGreeting, speakGreeting, _lineBankEvents: EVENTS };
})();
