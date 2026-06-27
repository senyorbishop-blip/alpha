import React, { useState, useMemo, useRef, useEffect } from "react";
import {
  Search, X, ScrollText, BookOpen, StickyNote, Landmark, Plus, Pin,
  Check, Circle, Coins, Sparkles, MapPin, User, Swords, Link2, Eye,
  Users, Lock, ChevronRight, Crown, Wand2
} from "lucide-react";

/* ──────────────────────────────────────────────────────────────────────────
   THE CODEX — a unified home for Quests, Session Log, Notes & Lore.
   Prototype to evaluate the layout: one store, type switcher, search + tags,
   visibility tiers, an objective tracker, and the signature linked-entry rail.
   ────────────────────────────────────────────────────────────────────────── */

const C = {
  ink: "#15110C",
  inkPanel: "#1E1812",
  inkRaise: "#261F17",
  inkLine: "#3A2F23",
  parch: "#ECE1C8",
  parchDim: "#B7A88A",
  muted: "#8C7F69",
  gold: "#CBA14C",
  goldDim: "#7C6533",
  ember: "#C2542F",
  sage: "#7C9A6E",
  lapis: "#6E93C4",
  lapisDim: "#3D556F",
};

const TYPES = [
  { id: "quest", label: "Quests", icon: Swords, tint: C.gold },
  { id: "log", label: "Session Log", icon: ScrollText, tint: C.parchDim },
  { id: "note", label: "Notes", icon: StickyNote, tint: C.lapis },
  { id: "lore", label: "Lore & People", icon: Landmark, tint: C.sage },
];

const VIS = {
  private: { label: "Private", icon: Lock, color: C.lapis, note: "Only you can see this." },
  party: { label: "Party", icon: Users, color: C.gold, note: "Shared with the whole party." },
  dm: { label: "DM only", icon: Crown, color: C.ember, note: "Hidden from players." },
};

/* ── seed data: grounded in the real quest template + journal fields ──────── */
const SEED = [
  {
    id: "q1", type: "quest", title: "Bounty: The Red Knife Captain",
    author: "Marrow (DM)", role: "dm", visibility: "party", pinned: true,
    difficulty: "Tier 1", giver: "Caravanserai Steward", location: "Broken Watchtower",
    updated: "2 min ago",
    body: "Merchants are pooling coin for proof the Red Knife captain is dealt with. Scouts report ambushes near a broken watchtower on the old salt road.",
    objectives: [
      { text: "Gather witness reports at the caravanserai", done: true },
      { text: "Track the raiders to the broken watchtower", done: true },
      { text: "Defeat or capture the Red Knife captain", done: false },
      { text: "Return proof to collect the bounty", done: false },
    ],
    rewards: { gold: 120, xp: 300, items: ["Stamped bounty writ", "Minor healing draught"] },
    links: [
      { kind: "npc", name: "Red Knife Captain" },
      { kind: "place", name: "Broken Watchtower" },
      { kind: "npc", name: "Caravanserai Steward" },
    ],
    tags: ["bounty", "goblins", "active"],
  },
  {
    id: "q2", type: "quest", title: "The Salt-Road Debt", visibility: "party",
    author: "Marrow (DM)", role: "dm", difficulty: "Tier 1", giver: "Vell the Broker",
    location: "Saltmarket", updated: "yesterday",
    body: "Vell will forgive the party's stabling debt if they recover a ledger lost when the last caravan scattered.",
    objectives: [
      { text: "Find the scattered caravan's strongbox", done: false },
      { text: "Recover Vell's ledger", done: false },
    ],
    rewards: { gold: 0, xp: 150, items: ["Debt forgiven", "Saltmarket goodwill"] },
    links: [{ kind: "npc", name: "Vell the Broker" }, { kind: "place", name: "Saltmarket" }],
    tags: ["favor", "social"],
  },
  {
    id: "l1", type: "log", title: "Session 7 — Ambush on the Salt Road",
    author: "Marrow (DM)", role: "dm", visibility: "party", updated: "2 days ago",
    body: "The party was jumped by Red Knife scouts at dusk. Brakka took an arrow but held the line; Sister Wen turned two goblins before they reached the wagons. They tracked the survivors toward the watchtower and made camp in the treeline.",
    links: [{ kind: "place", name: "Broken Watchtower" }, { kind: "npc", name: "Red Knife Captain" }],
    tags: ["recap", "combat"],
  },
  {
    id: "l2", type: "log", title: "Session 6 — Striking the Debt",
    author: "Marrow (DM)", role: "dm", visibility: "party", updated: "9 days ago",
    body: "Negotiated with Vell over the stabling debt. The party agreed to recover a lost ledger in exchange. Rumors of the Red Knife raids first surfaced here.",
    links: [{ kind: "npc", name: "Vell the Broker" }, { kind: "place", name: "Saltmarket" }],
    tags: ["recap", "social"],
  },
  {
    id: "n1", type: "note", title: "Don't trust the Steward", visibility: "private",
    author: "You (Brakka)", role: "player", updated: "1 min ago",
    body: "The Caravanserai Steward knew the captain's name before we said it. Keep the bounty proof until we're sure who's paying.",
    links: [{ kind: "npc", name: "Caravanserai Steward" }],
    tags: ["suspicion"],
  },
  {
    id: "n2", type: "note", title: "Party loot to split", visibility: "party",
    author: "You (Brakka)", role: "player", updated: "3 days ago",
    body: "Watchtower haul so far: 34 gp, a silvered dagger, and a sealed letter we haven't opened. Split after the captain's down.",
    links: [{ kind: "place", name: "Broken Watchtower" }],
    tags: ["loot"],
  },
  {
    id: "lo1", type: "lore", title: "Red Knife Captain", visibility: "dm",
    author: "Marrow (DM)", role: "dm", updated: "6 days ago",
    body: "Goblin warlord, ex-mercenary. Fights from the watchtower's upper floor and flees if reduced below half. Carries the steward's missing signet — proof the two are connected.",
    links: [{ kind: "place", name: "Broken Watchtower" }, { kind: "npc", name: "Caravanserai Steward" }],
    tags: ["npc", "antagonist"],
  },
  {
    id: "lo2", type: "lore", title: "Caravanserai Steward", visibility: "party",
    author: "Marrow (DM)", role: "dm", updated: "6 days ago",
    body: "Runs the waystation on the salt road. Friendly, generous with rumors — perhaps too generous.",
    links: [{ kind: "place", name: "Saltmarket" }],
    tags: ["npc", "questgiver"],
  },
];

const KIND_ICON = { npc: User, place: MapPin, item: Wand2 };

export default function CodexPrototype() {
  const [entries, setEntries] = useState(SEED);
  const [activeType, setActiveType] = useState("quest");
  const [query, setQuery] = useState("");
  const [linkFilter, setLinkFilter] = useState(null);
  const [selectedId, setSelectedId] = useState("q1");
  const [capturing, setCapturing] = useState(false);

  const counts = useMemo(() => {
    const m = {};
    for (const t of TYPES) m[t.id] = entries.filter((e) => e.type === t.id).length;
    return m;
  }, [entries]);

  const list = useMemo(() => {
    let r = entries.filter((e) => e.type === activeType);
    if (linkFilter) r = entries.filter((e) => e.links?.some((l) => l.name === linkFilter));
    if (query.trim()) {
      const q = query.toLowerCase();
      r = r.filter(
        (e) =>
          e.title.toLowerCase().includes(q) ||
          e.body.toLowerCase().includes(q) ||
          e.tags?.some((t) => t.includes(q))
      );
    }
    return r.sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));
  }, [entries, activeType, query, linkFilter]);

  const selected = entries.find((e) => e.id === selectedId);

  // backlinks: other entries that reference any subject this entry links to
  const backlinks = useMemo(() => {
    if (!selected) return [];
    const names = new Set((selected.links || []).map((l) => l.name));
    names.add(selected.title);
    return entries.filter(
      (e) => e.id !== selected.id && e.links?.some((l) => names.has(l.name))
    );
  }, [selected, entries]);

  const toggleObjective = (eid, idx) =>
    setEntries((prev) =>
      prev.map((e) =>
        e.id === eid
          ? { ...e, objectives: e.objectives.map((o, i) => (i === idx ? { ...o, done: !o.done } : o)) }
          : e
      )
    );

  const cycleVis = (eid) =>
    setEntries((prev) =>
      prev.map((e) => {
        if (e.id !== eid) return e;
        const order = ["private", "party", "dm"];
        return { ...e, visibility: order[(order.indexOf(e.visibility) + 1) % 3] };
      })
    );

  const togglePin = (eid) =>
    setEntries((prev) => prev.map((e) => (e.id === eid ? { ...e, pinned: !e.pinned } : e)));

  const addNote = (title, vis) => {
    const id = "n" + Math.random().toString(36).slice(2, 7);
    const e = {
      id, type: "note", title: title || "Untitled note", visibility: vis,
      author: "You (Brakka)", role: "player", updated: "just now",
      body: "", links: [], tags: ["new"],
    };
    setEntries((p) => [e, ...p]);
    setActiveType("note");
    setSelectedId(id);
    setCapturing(false);
  };

  const jumpToLink = (name) => {
    setLinkFilter(name);
    setQuery("");
  };

  return (
    <div style={{ ...styles.stage }}>
      <StyleTag />
      {/* dim "game table" backdrop so the drawer reads as an overlay */}
      <div style={styles.tableHint}>
        <div style={styles.tableGrid} />
        <div style={styles.tableLabel}>the table · session 7 in progress</div>
      </div>

      <div style={styles.drawer} className="cdx-drawer">
        <div style={styles.candle} />

        {/* ── header ─────────────────────────────────────────────── */}
        <header style={styles.header}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
            <span style={styles.brand}>Codex</span>
            <span style={styles.brandSub}>Saltmarch Campaign</span>
          </div>
          <div style={styles.searchWrap} className="cdx-search">
            <Search size={15} color={C.muted} />
            <input
              value={query}
              onChange={(e) => { setQuery(e.target.value); setLinkFilter(null); }}
              placeholder="Search every entry…"
              style={styles.search}
            />
          </div>
          <button style={styles.iconBtn} className="cdx-icon" aria-label="Close codex">
            <X size={18} />
          </button>
        </header>

        <div style={styles.body}>
          {/* ── type rail ───────────────────────────────────────── */}
          <nav style={styles.rail}>
            {TYPES.map((t) => {
              const on = activeType === t.id && !linkFilter;
              const Icon = t.icon;
              return (
                <button
                  key={t.id}
                  onClick={() => { setActiveType(t.id); setLinkFilter(null); }}
                  className="cdx-railbtn"
                  style={{
                    ...styles.railBtn,
                    background: on ? C.inkRaise : "transparent",
                    color: on ? C.parch : C.parchDim,
                    boxShadow: on ? `inset 2px 0 0 ${t.tint}` : "none",
                  }}
                >
                  <Icon size={16} color={on ? t.tint : C.muted} />
                  <span style={{ flex: 1, textAlign: "left" }}>{t.label}</span>
                  <span style={styles.count}>{counts[t.id]}</span>
                </button>
              );
            })}

            <div style={styles.railDivider} />
            <button className="cdx-railbtn" style={styles.captureBtn} onClick={() => setCapturing(true)}>
              <Plus size={16} color={C.ink} />
              Quick note
            </button>
            <p style={styles.railHint}>
              Captured private by default. Anyone at the table can keep their own
              entries.
            </p>
          </nav>

          {/* ── list pane ───────────────────────────────────────── */}
          <section style={styles.listPane}>
            {linkFilter && (
              <div style={styles.filterPill}>
                <Link2 size={13} color={C.lapis} />
                <span style={{ flex: 1 }}>
                  linked to <strong style={{ color: C.parch }}>{linkFilter}</strong>
                </span>
                <button onClick={() => setLinkFilter(null)} style={styles.pillX} className="cdx-icon">
                  <X size={13} />
                </button>
              </div>
            )}
            <div style={styles.listScroll} className="cdx-scroll">
              {list.length === 0 && (
                <div style={styles.empty}>
                  Nothing here yet. Capture the first one — it stays private until you share it.
                </div>
              )}
              {list.map((e) => (
                <EntryCard
                  key={e.id}
                  e={e}
                  active={e.id === selectedId}
                  onClick={() => setSelectedId(e.id)}
                />
              ))}
            </div>
          </section>

          {/* ── detail pane ─────────────────────────────────────── */}
          <section style={styles.detail} className="cdx-scroll">
            {selected ? (
              <Detail
                e={selected}
                backlinks={backlinks}
                onToggleObjective={toggleObjective}
                onCycleVis={cycleVis}
                onTogglePin={togglePin}
                onJump={jumpToLink}
                onOpen={(id) => setSelectedId(id)}
              />
            ) : (
              <div style={styles.empty}>Select an entry to read it.</div>
            )}
          </section>
        </div>
      </div>

      {capturing && <Capture onCancel={() => setCapturing(false)} onSave={addNote} />}
    </div>
  );
}

/* ── entry card ───────────────────────────────────────────────────────────── */
function EntryCard({ e, active, onClick }) {
  const v = VIS[e.visibility];
  const Vicon = v.icon;
  const done = e.objectives ? e.objectives.filter((o) => o.done).length : 0;
  const total = e.objectives ? e.objectives.length : 0;
  return (
    <button
      onClick={onClick}
      className="cdx-card"
      style={{
        ...styles.card,
        borderColor: active ? C.gold : C.inkLine,
        background: active ? C.inkRaise : "transparent",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {e.pinned && <Pin size={12} color={C.gold} fill={C.gold} />}
        <span style={styles.cardTitle}>{e.title}</span>
      </div>
      <p style={styles.cardBody}>{e.body || "Empty — tap to write."}</p>
      <div style={styles.cardMeta}>
        <span style={{ display: "flex", alignItems: "center", gap: 4, color: v.color }}>
          <Vicon size={11} /> {v.label}
        </span>
        {total > 0 && (
          <span style={{ color: done === total ? C.sage : C.parchDim }}>
            {done}/{total} done
          </span>
        )}
        <span style={{ flex: 1 }} />
        <span style={styles.cardWhen}>{e.updated}</span>
      </div>
      {e.tags && (
        <div style={styles.tagRow}>
          {e.tags.map((t) => (
            <span key={t} style={styles.tag}>#{t}</span>
          ))}
        </div>
      )}
    </button>
  );
}

/* ── detail pane ──────────────────────────────────────────────────────────── */
function Detail({ e, backlinks, onToggleObjective, onCycleVis, onTogglePin, onJump, onOpen }) {
  const v = VIS[e.visibility];
  const Vicon = v.icon;
  const done = e.objectives ? e.objectives.filter((o) => o.done).length : 0;
  const total = e.objectives ? e.objectives.length : 0;
  const pct = total ? Math.round((done / total) * 100) : 0;

  return (
    <div style={{ padding: "22px 26px 40px" }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <h1 style={styles.title}>{e.title}</h1>
        <button className="cdx-icon" style={styles.iconBtn} onClick={() => onTogglePin(e.id)} aria-label="Pin">
          <Pin size={16} color={e.pinned ? C.gold : C.muted} fill={e.pinned ? C.gold : "none"} />
        </button>
      </div>

      <div style={styles.detailMeta}>
        <button onClick={() => onCycleVis(e.id)} className="cdx-vis" style={{ ...styles.visChip, color: v.color, borderColor: v.color + "55" }}>
          <Vicon size={12} /> {v.label}
          <ChevronRight size={11} style={{ opacity: 0.5 }} />
        </button>
        <span style={styles.byline}>
          {e.role === "dm" ? <Crown size={12} color={C.ember} /> : <User size={12} color={C.lapis} />}
          {e.author}
        </span>
        <span style={styles.byline}>· {e.updated}</span>
      </div>
      <p style={styles.visNote}>{v.note}</p>

      {/* quest-specific scaffold */}
      {e.type === "quest" && (
        <div style={styles.questStrip}>
          {e.difficulty && <Chip icon={Swords} text={e.difficulty} />}
          {e.giver && <Chip icon={User} text={e.giver} />}
          {e.location && <Chip icon={MapPin} text={e.location} />}
        </div>
      )}

      <p style={styles.bodyText}>{e.body}</p>

      {/* objective tracker — first-class, checkable */}
      {total > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionHead}>
            <span style={styles.sectionLabel}>Objectives</span>
            <span style={{ color: pct === 100 ? C.sage : C.gold, fontSize: 12, fontFamily: "'Spline Sans Mono', monospace" }}>
              {pct}%
            </span>
          </div>
          <div style={styles.progressTrack}>
            <div style={{ ...styles.progressFill, width: `${pct}%`, background: pct === 100 ? C.sage : C.gold }} />
          </div>
          <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 2 }}>
            {e.objectives.map((o, i) => (
              <button key={i} onClick={() => onToggleObjective(e.id, i)} className="cdx-obj" style={styles.objRow}>
                <span style={{ ...styles.objBox, borderColor: o.done ? C.sage : C.muted, background: o.done ? C.sage : "transparent" }}>
                  {o.done ? <Check size={12} color={C.ink} strokeWidth={3} /> : <Circle size={6} color={C.muted} />}
                </span>
                <span style={{ color: o.done ? C.muted : C.parch, textDecoration: o.done ? "line-through" : "none", textAlign: "left" }}>
                  {o.text}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* rewards */}
      {e.rewards && (
        <div style={styles.section}>
          <span style={styles.sectionLabel}>On completion</span>
          <div style={styles.rewardRow}>
            {e.rewards.gold > 0 && <Reward icon={Coins} text={`${e.rewards.gold} gp`} color={C.gold} />}
            {e.rewards.xp > 0 && <Reward icon={Sparkles} text={`${e.rewards.xp} xp`} color={C.lapis} />}
            {e.rewards.items.map((it) => (
              <Reward key={it} icon={Wand2} text={it} color={C.parchDim} />
            ))}
          </div>
        </div>
      )}

      {/* SIGNATURE: links + backlinks rail */}
      <div style={styles.section}>
        <span style={styles.sectionLabel}>Connections</span>
        {(e.links?.length > 0) ? (
          <div style={styles.linkWrap}>
            {e.links.map((l) => {
              const Icon = KIND_ICON[l.kind] || Link2;
              return (
                <button key={l.name} onClick={() => onJump(l.name)} className="cdx-link" style={styles.linkChip}>
                  <Icon size={12} color={C.lapis} />
                  {l.name}
                </button>
              );
            })}
          </div>
        ) : (
          <p style={styles.thin}>No links yet. Type @ to connect a person, place, or item.</p>
        )}

        {backlinks.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <span style={styles.backlinkLabel}>
              <Link2 size={11} color={C.muted} /> appears in {backlinks.length} other {backlinks.length === 1 ? "entry" : "entries"}
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
              {backlinks.map((b) => {
                const t = TYPES.find((x) => x.id === b.type);
                const Icon = t.icon;
                return (
                  <button key={b.id} onClick={() => onOpen(b.id)} className="cdx-back" style={styles.backRow}>
                    <Icon size={12} color={t.tint} />
                    <span style={{ flex: 1, textAlign: "left", color: C.parchDim }}>{b.title}</span>
                    <ChevronRight size={13} color={C.muted} />
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const Chip = ({ icon: Icon, text }) => (
  <span style={styles.metaChip}><Icon size={12} color={C.muted} />{text}</span>
);
const Reward = ({ icon: Icon, text, color }) => (
  <span style={{ ...styles.reward, color }}><Icon size={12} color={color} />{text}</span>
);

/* ── quick capture ────────────────────────────────────────────────────────── */
function Capture({ onCancel, onSave }) {
  const [title, setTitle] = useState("");
  const [vis, setVis] = useState("private");
  const ref = useRef(null);
  useEffect(() => ref.current?.focus(), []);
  return (
    <div style={styles.modalWrap} onClick={onCancel}>
      <div style={styles.modal} onClick={(ev) => ev.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <StickyNote size={16} color={C.lapis} />
          <span style={styles.modalTitle}>New note</span>
        </div>
        <input
          ref={ref}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSave(title, vis)}
          placeholder="What do you want to remember?"
          style={styles.modalInput}
        />
        <div style={{ display: "flex", gap: 8, margin: "16px 0 20px" }}>
          {Object.entries(VIS).map(([k, vv]) => {
            const Icon = vv.icon;
            const on = vis === k;
            return (
              <button key={k} onClick={() => setVis(k)} className="cdx-vispick" style={{
                ...styles.visPick,
                borderColor: on ? vv.color : C.inkLine,
                color: on ? vv.color : C.muted,
                background: on ? vv.color + "14" : "transparent",
              }}>
                <Icon size={13} /> {vv.label}
              </button>
            );
          })}
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button onClick={onCancel} className="cdx-ghost" style={styles.ghostBtn}>Cancel</button>
          <button onClick={() => onSave(title, vis)} className="cdx-primary" style={styles.primaryBtn}>Save note</button>
        </div>
      </div>
    </div>
  );
}

/* ── style tag (fonts, pseudo-states, scrollbar, motion) ──────────────────── */
function StyleTag() {
  return (
    <style>{`
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Spline+Sans:wght@400;500;600&family=Spline+Sans+Mono:wght@400;500&display=swap');
      * { box-sizing: border-box; }
      .cdx-drawer { animation: cdxSlide .42s cubic-bezier(.2,.8,.2,1); }
      @keyframes cdxSlide { from { transform: translateX(26px); opacity: 0 } to { transform: none; opacity: 1 } }
      .cdx-scroll::-webkit-scrollbar { width: 9px }
      .cdx-scroll::-webkit-scrollbar-thumb { background: ${C.inkLine}; border-radius: 9px }
      .cdx-scroll::-webkit-scrollbar-track { background: transparent }
      .cdx-card:hover { border-color: ${C.goldDim} !important; }
      .cdx-railbtn:hover { color: ${C.parch} !important; }
      .cdx-link:hover { border-color: ${C.lapis} !important; color: ${C.parch} !important; box-shadow: 0 0 14px -4px ${C.lapis}; }
      .cdx-back:hover { background: ${C.inkRaise} !important; }
      .cdx-obj:hover span:last-child { color: ${C.parch} !important; }
      .cdx-icon:hover { color: ${C.parch} !important; }
      .cdx-vis:hover { filter: brightness(1.25); }
      .cdx-primary:hover { filter: brightness(1.1); }
      .cdx-ghost:hover { color: ${C.parch} !important; }
      .cdx-vispick:hover { filter: brightness(1.2); }
      button:focus-visible, input:focus-visible { outline: 2px solid ${C.gold}; outline-offset: 2px; }
      input::placeholder { color: ${C.muted}; }
      @media (prefers-reduced-motion: reduce) { .cdx-drawer { animation: none } }
    `}</style>
  );
}

/* ── styles ───────────────────────────────────────────────────────────────── */
const font = "'Spline Sans', system-ui, sans-serif";
const styles = {
  stage: {
    position: "relative", height: "100vh", width: "100%", background: "#0C0A07",
    fontFamily: font, color: C.parch, overflow: "hidden", display: "flex",
    justifyContent: "flex-end",
  },
  tableHint: { position: "absolute", inset: 0, padding: 28, opacity: 0.5 },
  tableGrid: {
    position: "absolute", inset: 0,
    backgroundImage:
      `radial-gradient(circle at 30% 40%, #1a140d 0%, #0C0A07 60%),
       linear-gradient(${C.inkLine}55 1px, transparent 1px),
       linear-gradient(90deg, ${C.inkLine}55 1px, transparent 1px)`,
    backgroundSize: "100% 100%, 46px 46px, 46px 46px",
  },
  tableLabel: {
    position: "absolute", left: 30, top: 24, fontFamily: "'Spline Sans Mono', monospace",
    fontSize: 12, letterSpacing: 1, color: C.muted, textTransform: "uppercase",
  },
  drawer: {
    position: "relative", height: "100%", width: "min(980px, 100%)",
    background: `linear-gradient(${C.inkPanel}, ${C.ink})`,
    borderLeft: `1px solid ${C.inkLine}`,
    boxShadow: "-30px 0 80px -20px rgba(0,0,0,.7)",
    display: "flex", flexDirection: "column", overflow: "hidden",
  },
  candle: {
    position: "absolute", top: -120, left: "50%", transform: "translateX(-50%)",
    width: 520, height: 260, pointerEvents: "none",
    background: `radial-gradient(ellipse at center, ${C.gold}22, transparent 70%)`,
  },
  header: {
    display: "flex", alignItems: "center", gap: 16, padding: "16px 20px",
    borderBottom: `1px solid ${C.inkLine}`, position: "relative", zIndex: 1,
  },
  brand: { fontFamily: "'Fraunces', serif", fontSize: 24, fontWeight: 600, color: C.parch, letterSpacing: 0.5 },
  brandSub: { fontFamily: "'Spline Sans Mono', monospace", fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: 1.5 },
  searchWrap: {
    marginLeft: "auto", display: "flex", alignItems: "center", gap: 8,
    background: C.ink, border: `1px solid ${C.inkLine}`, borderRadius: 8,
    padding: "8px 12px", width: 280,
  },
  search: { background: "transparent", border: "none", color: C.parch, outline: "none", fontSize: 13, width: "100%", fontFamily: font },
  iconBtn: { background: "transparent", border: "none", color: C.muted, cursor: "pointer", padding: 6, display: "flex", borderRadius: 6 },
  body: { display: "flex", flex: 1, minHeight: 0 },

  rail: { width: 192, borderRight: `1px solid ${C.inkLine}`, padding: 12, display: "flex", flexDirection: "column", gap: 2 },
  railBtn: {
    display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 7,
    border: "none", cursor: "pointer", fontSize: 13.5, fontFamily: font, fontWeight: 500, transition: "all .15s",
  },
  count: { fontFamily: "'Spline Sans Mono', monospace", fontSize: 11, color: C.muted },
  railDivider: { height: 1, background: C.inkLine, margin: "12px 4px" },
  captureBtn: {
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "10px",
    borderRadius: 7, border: "none", cursor: "pointer", fontWeight: 600, fontSize: 13, fontFamily: font,
    background: C.gold, color: C.ink,
  },
  railHint: { fontSize: 11.5, lineHeight: 1.5, color: C.muted, marginTop: 12, padding: "0 4px" },

  listPane: { width: 320, borderRight: `1px solid ${C.inkLine}`, display: "flex", flexDirection: "column", minHeight: 0 },
  filterPill: {
    display: "flex", alignItems: "center", gap: 8, margin: 12, padding: "8px 10px",
    background: C.lapisDim + "33", border: `1px solid ${C.lapisDim}`, borderRadius: 7, fontSize: 12.5, color: C.parchDim,
  },
  pillX: { background: "transparent", border: "none", color: C.muted, cursor: "pointer", display: "flex", padding: 2 },
  listScroll: { overflowY: "auto", padding: 12, paddingTop: 6, display: "flex", flexDirection: "column", gap: 8, flex: 1 },
  card: {
    textAlign: "left", border: "1px solid", borderRadius: 9, padding: "12px 13px", cursor: "pointer",
    fontFamily: font, transition: "all .15s", display: "flex", flexDirection: "column", gap: 7,
  },
  cardTitle: { fontFamily: "'Fraunces', serif", fontSize: 15.5, fontWeight: 600, color: C.parch, lineHeight: 1.2 },
  cardBody: { fontSize: 12.5, lineHeight: 1.5, color: C.parchDim, margin: 0, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" },
  cardMeta: { display: "flex", alignItems: "center", gap: 10, fontSize: 11, fontFamily: "'Spline Sans Mono', monospace" },
  cardWhen: { color: C.muted },
  tagRow: { display: "flex", flexWrap: "wrap", gap: 5 },
  tag: { fontSize: 10.5, fontFamily: "'Spline Sans Mono', monospace", color: C.goldDim, background: C.gold + "12", padding: "2px 6px", borderRadius: 4 },

  detail: { flex: 1, overflowY: "auto", minWidth: 0 },
  title: { fontFamily: "'Fraunces', serif", fontSize: 28, fontWeight: 600, color: C.parch, margin: 0, lineHeight: 1.15, flex: 1 },
  detailMeta: { display: "flex", alignItems: "center", gap: 12, marginTop: 14, flexWrap: "wrap" },
  visChip: { display: "flex", alignItems: "center", gap: 5, padding: "4px 9px", borderRadius: 20, border: "1px solid", background: "transparent", cursor: "pointer", fontSize: 11.5, fontWeight: 500, fontFamily: font },
  byline: { display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: C.muted },
  visNote: { fontSize: 11.5, color: C.muted, marginTop: 8, fontStyle: "italic" },
  questStrip: { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 18 },
  metaChip: { display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: C.parchDim, background: C.inkRaise, padding: "5px 10px", borderRadius: 6, border: `1px solid ${C.inkLine}` },
  bodyText: { fontSize: 14.5, lineHeight: 1.7, color: C.parchDim, marginTop: 20 },

  section: { marginTop: 28, paddingTop: 20, borderTop: `1px solid ${C.inkLine}` },
  sectionHead: { display: "flex", alignItems: "center", justifyContent: "space-between" },
  sectionLabel: { fontFamily: "'Spline Sans Mono', monospace", fontSize: 11, letterSpacing: 1.5, textTransform: "uppercase", color: C.muted },
  progressTrack: { height: 6, background: C.ink, borderRadius: 6, marginTop: 12, overflow: "hidden", border: `1px solid ${C.inkLine}` },
  progressFill: { height: "100%", borderRadius: 6, transition: "width .4s cubic-bezier(.2,.8,.2,1)" },
  objRow: { display: "flex", alignItems: "center", gap: 11, padding: "8px 6px", background: "transparent", border: "none", cursor: "pointer", fontFamily: font, fontSize: 14, borderRadius: 6 },
  objBox: { width: 20, height: 20, minWidth: 20, borderRadius: 6, border: "2px solid", display: "flex", alignItems: "center", justifyContent: "center", transition: "all .15s" },
  rewardRow: { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 },
  reward: { display: "flex", alignItems: "center", gap: 6, fontSize: 12.5, fontWeight: 500, padding: "6px 11px", borderRadius: 6, background: C.inkRaise, border: `1px solid ${C.inkLine}` },

  linkWrap: { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 },
  linkChip: { display: "flex", alignItems: "center", gap: 6, padding: "6px 11px", borderRadius: 20, border: `1px solid ${C.lapisDim}`, background: C.lapisDim + "1A", color: C.parchDim, cursor: "pointer", fontSize: 12.5, fontFamily: font, transition: "all .18s" },
  backlinkLabel: { display: "flex", alignItems: "center", gap: 6, fontSize: 11.5, color: C.muted, fontFamily: "'Spline Sans Mono', monospace" },
  backRow: { display: "flex", alignItems: "center", gap: 9, padding: "8px 10px", borderRadius: 7, border: `1px solid ${C.inkLine}`, background: "transparent", cursor: "pointer", fontSize: 13, fontFamily: font, transition: "all .15s" },
  thin: { fontSize: 12.5, color: C.muted, marginTop: 10, fontStyle: "italic" },
  empty: { padding: 40, color: C.muted, fontSize: 13.5, lineHeight: 1.6, textAlign: "center", maxWidth: 320, margin: "40px auto" },

  modalWrap: { position: "absolute", inset: 0, background: "rgba(8,6,4,.66)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 20, backdropFilter: "blur(2px)" },
  modal: { width: 440, background: C.inkPanel, border: `1px solid ${C.inkLine}`, borderRadius: 14, padding: 22, boxShadow: "0 30px 80px -20px rgba(0,0,0,.8)" },
  modalTitle: { fontFamily: "'Fraunces', serif", fontSize: 18, fontWeight: 600, color: C.parch },
  modalInput: { width: "100%", background: C.ink, border: `1px solid ${C.inkLine}`, borderRadius: 8, padding: "12px 14px", color: C.parch, fontSize: 14.5, outline: "none", fontFamily: font },
  visPick: { flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "9px", borderRadius: 8, border: "1px solid", cursor: "pointer", fontSize: 12.5, fontWeight: 500, fontFamily: font, transition: "all .15s" },
  ghostBtn: { background: "transparent", border: "none", color: C.muted, cursor: "pointer", padding: "9px 16px", fontSize: 13.5, fontFamily: font },
  primaryBtn: { background: C.gold, color: C.ink, border: "none", borderRadius: 8, cursor: "pointer", padding: "9px 18px", fontSize: 13.5, fontWeight: 600, fontFamily: font },
};
