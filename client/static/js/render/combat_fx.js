(function(){
  function _pointFromToken(env, tokenId) {
    const tok = env.getToken(tokenId);
    if (!tok) return null;
    const cx = Number(tok.x || 0) + Number(tok.width || 0) / 2;
    const cy = Number(tok.y || 0) + Number(tok.height || 0) / 2;
    return env.worldToScreen(cx, cy);
  }
  function _node(env, wrap, styles) {
    const el = env.document.createElement('div');
    el.style.position = 'absolute';
    el.style.pointerEvents = 'none';
    el.style.zIndex = '10025';
    Object.entries(styles || {}).forEach(([k, v]) => { el.style[k] = v; });
    wrap.appendChild(el);
    return el;
  }
  function pulseTarget(env, tokenId) {
    const wrap = env.document.getElementById('canvas-wrap') || env.document.body;
    const pt = _pointFromToken(env, tokenId);
    if (!wrap || !pt) return;
    const ring = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y}px`, width:'42px', height:'42px', marginLeft:'-21px', marginTop:'-21px', borderRadius:'999px', border:'2px solid rgba(255,220,120,0.92)', boxShadow:'0 0 18px rgba(255,205,90,0.42)', transform:'scale(0.4)', opacity:'0.95' });
    const halo = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y}px`, width:'20px', height:'20px', marginLeft:'-10px', marginTop:'-10px', borderRadius:'999px', background:'radial-gradient(circle, rgba(255,247,214,0.98), rgba(255,195,74,0.55) 48%, rgba(255,195,74,0) 78%)', transform:'scale(0.3)', opacity:'1' });
    requestAnimationFrame(() => {
      ring.style.transition='transform 420ms cubic-bezier(.18,.74,.18,1), opacity 520ms ease';
      ring.style.transform='scale(2.6)';
      ring.style.opacity='0';
      halo.style.transition='transform 340ms ease, opacity 420ms ease';
      halo.style.transform='scale(2.1)';
      halo.style.opacity='0';
    });
    setTimeout(() => { ring.remove(); halo.remove(); }, 700);
  }
  function _animateHitShake(target, transformFrom, transformTo) {
    let raf = 0;
    const start = performance.now();
    function step(now) {
      const t = Math.min(1, (now - start) / 340);
      const damp = 1 - t;
      const wobbleX = Math.sin(t * 33) * 9 * damp;
      const wobbleY = Math.sin(t * 20) * 3 * damp;
      target.style.transform = `${transformFrom} translate(${wobbleX.toFixed(2)}px, ${wobbleY.toFixed(2)}px)`;
      if (t < 1) {
        raf = requestAnimationFrame(step);
      } else {
        target.style.transition = 'transform 140ms ease-out, opacity 220ms ease';
        target.style.transform = transformTo;
        target.style.opacity = '0';
      }
    }
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }
  function _createMeleeHit(env, wrap, pt) {
    const backGlow = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y}px`, width:'118px', height:'118px', marginLeft:'-59px', marginTop:'-59px', borderRadius:'999px', background:'radial-gradient(circle, rgba(255,236,183,0.95), rgba(255,171,82,0.55) 35%, rgba(112,36,10,0.22) 62%, rgba(112,36,10,0) 78%)', opacity:'0.88', transform:'scale(0.42)', filter:'blur(1px)' });
    const slashCore = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y}px`, width:'146px', height:'24px', marginLeft:'-73px', marginTop:'-12px', background:'linear-gradient(90deg, rgba(255,255,255,0), rgba(255,248,221,0.98) 18%, rgba(255,214,124,0.96) 48%, rgba(255,141,61,0.94) 72%, rgba(182,55,18,0.9) 100%)', clipPath:'polygon(0% 50%, 55% 24%, 82% 0%, 100% 50%, 82% 100%, 55% 76%, 0% 50%)', transform:'rotate(-21deg) translateX(-40px) scale(0.58)', opacity:'0.98', filter:'drop-shadow(0 0 13px rgba(255,184,96,0.52))' });
    const slashEcho = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y+8}px`, width:'120px', height:'14px', marginLeft:'-60px', marginTop:'-7px', background:'linear-gradient(90deg, rgba(255,255,255,0), rgba(255,230,171,0.88) 28%, rgba(255,126,62,0.78) 66%, rgba(255,126,62,0) 100%)', clipPath:'polygon(0% 48%, 70% 22%, 100% 50%, 70% 78%, 0% 52%)', transform:'rotate(17deg) translateX(-18px) scale(0.62)', opacity:'0.72', filter:'blur(0.4px)' });
    const impactCore = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y}px`, width:'34px', height:'34px', marginLeft:'-17px', marginTop:'-17px', borderRadius:'999px', background:'radial-gradient(circle, rgba(255,255,255,0.98), rgba(255,232,176,0.96) 30%, rgba(255,128,65,0.24) 72%)', transform:'scale(0.32)', opacity:'1', boxShadow:'0 0 18px rgba(255,188,113,0.42)' });
    const emberRing = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y}px`, width:'72px', height:'72px', marginLeft:'-36px', marginTop:'-36px', borderRadius:'999px', border:'2px solid rgba(255,189,116,0.76)', boxShadow:'0 0 18px rgba(255,145,74,0.24)', transform:'scale(0.36)', opacity:'0.94' });
    const hitBadge = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y-28}px`, transform:'translate(-50%, -50%) scale(0.72)', padding:'0.34rem 0.78rem', borderRadius:'999px', background:'linear-gradient(180deg, rgba(176,77,28,0.96), rgba(96,34,14,0.8))', border:'1px solid rgba(255,236,216,0.42)', color:'#fff6ee', fontFamily:"'Cinzel', serif", letterSpacing:'0.15em', boxShadow:'0 12px 28px rgba(25,9,4,0.26), 0 0 18px rgba(255,150,94,0.22)' });
    hitBadge.textContent = 'HIT';
    const cleanupShake = _animateHitShake(impactCore, 'scale(0.32)', 'scale(2.6)');
    requestAnimationFrame(() => {
      backGlow.style.transition='transform 320ms cubic-bezier(.18,.74,.18,1), opacity 520ms ease';
      backGlow.style.transform='scale(1.68)';
      backGlow.style.opacity='0';
      slashCore.style.transition='transform 280ms cubic-bezier(.18,.74,.18,1), opacity 420ms ease';
      slashCore.style.transform='rotate(-21deg) translateX(22px) scale(1.05)';
      slashCore.style.opacity='0';
      slashEcho.style.transition='transform 360ms cubic-bezier(.18,.74,.18,1), opacity 460ms ease';
      slashEcho.style.transform='rotate(17deg) translateX(18px) scale(1.12)';
      slashEcho.style.opacity='0';
      emberRing.style.transition='transform 360ms ease, opacity 520ms ease';
      emberRing.style.transform='scale(1.7)';
      emberRing.style.opacity='0';
      hitBadge.style.transition='transform 520ms ease, opacity 560ms ease';
      hitBadge.style.transform='translate(-50%, -96%) scale(1.03)';
      hitBadge.style.opacity='0';
    });
    setTimeout(() => { cleanupShake(); [backGlow, slashCore, slashEcho, impactCore, emberRing, hitBadge].forEach(n => n.remove()); }, 760);
  }
  function _createSpellHit(env, wrap, pt) {
    const aura = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y}px`, width:'126px', height:'126px', marginLeft:'-63px', marginTop:'-63px', borderRadius:'999px', background:'radial-gradient(circle, rgba(243,250,255,0.96), rgba(139,204,255,0.78) 24%, rgba(93,112,255,0.5) 46%, rgba(56,72,196,0.16) 68%, rgba(56,72,196,0) 82%)', opacity:'0.92', transform:'scale(0.28)', filter:'blur(0.8px)' });
    const beam = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y-8}px`, width:'26px', height:'128px', marginLeft:'-13px', marginTop:'-64px', background:'linear-gradient(180deg, rgba(255,255,255,0), rgba(233,245,255,0.98) 24%, rgba(161,218,255,0.98) 46%, rgba(93,116,255,0.88) 78%, rgba(93,116,255,0) 100%)', borderRadius:'999px', transform:'scaleY(0.2)', opacity:'0.96', filter:'drop-shadow(0 0 18px rgba(120,170,255,0.52))' });
    const innerCore = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y}px`, width:'32px', height:'32px', marginLeft:'-16px', marginTop:'-16px', borderRadius:'999px', background:'radial-gradient(circle, rgba(255,255,255,0.98), rgba(205,235,255,0.97) 30%, rgba(117,148,255,0.2) 72%)', transform:'scale(0.34)', opacity:'1', boxShadow:'0 0 22px rgba(127,176,255,0.46)' });
    const shockRing = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y}px`, width:'84px', height:'84px', marginLeft:'-42px', marginTop:'-42px', borderRadius:'999px', border:'2px solid rgba(191,223,255,0.86)', boxShadow:'0 0 20px rgba(110,156,255,0.3)', transform:'scale(0.26)', opacity:'0.96' });
    const motes = [];
    [
      [-42, -18], [36, -26], [-32, 28], [28, 24], [0, -42], [0, 42]
    ].forEach(([dx, dy], idx) => {
      const mote = _node(env, wrap, { left:`${pt.x + dx}px`, top:`${pt.y + dy}px`, width:'8px', height:'8px', marginLeft:'-4px', marginTop:'-4px', borderRadius:'999px', background: idx % 2 ? 'rgba(182,229,255,0.96)' : 'rgba(255,255,255,0.98)', boxShadow:'0 0 14px rgba(148,198,255,0.46)', transform:'scale(0.2)', opacity:'0.9' });
      motes.push({ node: mote, dx, dy });
    });
    const badge = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y-28}px`, transform:'translate(-50%, -50%) scale(0.72)', padding:'0.34rem 0.82rem', borderRadius:'999px', background:'linear-gradient(180deg, rgba(74,106,255,0.95), rgba(35,49,132,0.82))', border:'1px solid rgba(233,243,255,0.44)', color:'#f8fbff', fontFamily:"'Cinzel', serif", letterSpacing:'0.14em', boxShadow:'0 12px 26px rgba(9,18,60,0.28), 0 0 18px rgba(98,142,255,0.26)' });
    badge.textContent = 'SPELL HIT';
    const cleanupShake = _animateHitShake(innerCore, 'scale(0.34)', 'scale(2.9)');
    requestAnimationFrame(() => {
      aura.style.transition='transform 340ms cubic-bezier(.18,.74,.18,1), opacity 520ms ease';
      aura.style.transform='scale(1.84)';
      aura.style.opacity='0';
      beam.style.transition='transform 240ms cubic-bezier(.18,.74,.18,1), opacity 420ms ease';
      beam.style.transform='scaleY(1.18)';
      beam.style.opacity='0';
      shockRing.style.transition='transform 380ms ease, opacity 540ms ease';
      shockRing.style.transform='scale(1.96)';
      shockRing.style.opacity='0';
      badge.style.transition='transform 540ms ease, opacity 560ms ease';
      badge.style.transform='translate(-50%, -96%) scale(1.03)';
      badge.style.opacity='0';
      motes.forEach(({ node, dx, dy }) => {
        node.style.transition='transform 420ms cubic-bezier(.18,.74,.18,1), opacity 520ms ease';
        node.style.transform=`translate(${dx * 0.22}px, ${dy * 0.22}px) scale(1.4)`;
        node.style.opacity='0';
      });
    });
    setTimeout(() => { cleanupShake(); [aura, beam, innerCore, shockRing, badge, ...motes.map(m => m.node)].forEach(n => n.remove()); }, 800);
  }
  function showAttackResult(env, payload) {
    const wrap = env.document.getElementById('canvas-wrap') || env.document.body;
    const pt = _pointFromToken(env, payload.target_token_id) || { x: wrap.clientWidth / 2, y: wrap.clientHeight / 2 };
    if (payload.result === 'miss') {
      const miss = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y-22}px`, transform:'translate(-50%, -50%) scale(0.7)', padding:'0.32rem 0.7rem', borderRadius:'999px', background:'linear-gradient(180deg, rgba(80,70,68,0.92), rgba(45,38,36,0.78))', border:'1px solid rgba(231,208,194,0.38)', color:'#f7e8de', fontFamily:"'Cinzel', serif", letterSpacing:'0.12em', boxShadow:'0 0 18px rgba(0,0,0,0.24)' });
      miss.textContent='MISS';
      const arc = _node(env, wrap, { left:`${pt.x}px`, top:`${pt.y}px`, width:'90px', height:'90px', marginLeft:'-45px', marginTop:'-45px', borderRadius:'999px', borderTop:'3px solid rgba(245,226,214,0.78)', borderRight:'3px solid rgba(245,226,214,0.18)', borderBottom:'3px solid transparent', borderLeft:'3px solid transparent', transform:'rotate(-24deg) scale(0.4)', opacity:'0.9', filter:'blur(0.2px)' });
      requestAnimationFrame(() => {
        miss.style.transition='transform 520ms ease, opacity 560ms ease';
        miss.style.transform='translate(-50%, -88%) scale(1.06)';
        miss.style.opacity='0';
        arc.style.transition='transform 420ms cubic-bezier(.18,.74,.18,1), opacity 520ms ease';
        arc.style.transform='rotate(26deg) scale(1.18)';
        arc.style.opacity='0';
      });
      setTimeout(() => { miss.remove(); arc.remove(); }, 700);
      return;
    }
    const spell = String(payload.attack_kind || 'weapon') === 'spell';
    if (spell) {
      _createSpellHit(env, wrap, pt);
      return;
    }
    _createMeleeHit(env, wrap, pt);
  }
  window.AppCombatFX = { pulseTarget, showAttackResult };
})();
