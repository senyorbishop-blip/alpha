# Known Issues and Beta Notes (Founder Beta)

This document sets expectations for founder-beta testers.

## Beta status

- Current channel: founder beta
- Expect occasional rough edges
- Core gameplay is usable for active founder testing, but release-candidate hardening is still in progress

## Current known limitations

- Runtime architecture still has legacy/compatibility seams around `client/templates/play.html`.
- DM/prep experience is desktop-first; mobile phone support is best-effort for players.
- Some advanced AI/audio/image workflows depend on optional third-party API keys.
- Public internet hosting quality depends heavily on operator proxy/TLS/firewall setup.

## New systems: founder-beta readiness snapshot

This section is intentionally conservative: these systems are available for founder-beta testing, but none should be treated as "finished" or fully automated.

| System | Founder-beta status | Practical limitation to communicate |
|---|---|---|
| Living world state | Usable for active campaign testing | Long-running campaign drift still depends on regular DM review of state changes and save/restore checks. |
| Campaign hub | Usable for DM/session organization | Hub workflows are functional, but operators should still keep manual release notes and campaign handoff notes. |
| Faction reputation | Active and tracked | Reputation visibility can be role-scoped; DMs should verify player-facing visibility before sessions. |
| Guild rank | Active and derived from progression | Rank gating is only as reliable as quest completion hygiene; validate required-rank quests during prep. |
| Big-screen mode | Available for table display | Presentation mode hides controls by design and should be tested in-venue before live play. |
| Assistant DM permissions | Available with role controls | Permission boundaries are still a high-sensitivity area; verify assistant actions in a multi-role smoke test. |
| Split-party support | Available for session coordination | Rejoin/context switching should be tested when party state changes quickly. |
| Prep packs | Available for rapid session bootstrap | Imported content is starter-quality; DMs should review imported quests/handouts/encounters/POIs before play. |
| Cinematic overlays | Available for presentation polish | Overlay timing/content remains DM-operated and should be rehearsed to avoid blocking gameplay visibility. |

## Explicit support boundaries

- Do **not** assume full mobile DM support.
- Do **not** assume managed SaaS hosting is included; this repo is self-host oriented.
- Do **not** assume uninterrupted premium voice/image provider availability.

## Operational caveats

- Missing/rotating admin keys can break predictable admin workflows.
- Misconfigured proxy headers can affect auth/security behavior. If deployed behind
  nginx/Apache/Caddy and rate-limiting or IP logging seems wrong, check that
  `TRUST_PROXY_HEADERS=true` is set. See `docs/hosting-access-guide.md` for the full
  setup note and proxy config snippets. The server logs a warning at startup when this
  setting looks misconfigured for production.
- First-time startup on new environments may require dependency/tooling tuning.

## Reporting guidance

When filing founder-beta issues, include:

- deployment mode (local/LAN/public)
- OS + Python version
- browser + device type
- exact reproduction steps
- expected vs actual behavior
- relevant server log snippets

## Tone and expectation

Founder beta means stable-enough for real testing, with transparent limits and fast iteration based on feedback.
