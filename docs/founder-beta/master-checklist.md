# Founder Beta Master Checklist

Use this before sending any founder-beta build to external testers.

## A) Release metadata and package integrity

- [ ] `VERSION` matches intended release tag/build.
- [ ] `CHANGELOG.md` includes this release.
- [ ] Release notes exist under `docs/releases/`.
- [ ] Known issues list reviewed and updated.
- [ ] Release zip/package opens and includes required docs/config examples.

## B) Config and docs readiness

- [ ] `.env.example` is present and accurate.
- [ ] `config.txt.example` is present and accurate.
- [ ] DM, player, and admin docs are present.
- [ ] Founder beta reporting instructions are included.

## C) Install/startup validation

- [ ] Clean install tested on a fresh environment.
- [ ] App boot tested with documented startup command.
- [ ] Localhost access verified (`http://localhost:8000`).
- [ ] External device access verified (LAN or hosted URL).

## D) Core role workflow checks

- [ ] DM workflow smoke-tested (session start, map interaction, controls).
- [ ] Player join flow tested (invite/session code path).
- [ ] Viewer role tested if used in this beta wave.
- [ ] Save/load roundtrip verified.
- [ ] Reconnect behavior tested.
- [ ] Assistant DM permissions verified with DM + assistant/user role checks.
- [ ] Split-party assign/context flows verified (including rejoin behavior).
- [ ] Big-screen mode tested in the target display setup.
- [ ] Cinematic overlay start/stop tested without blocking map readability.
- [ ] Campaign hub / living-world updates sanity-checked after save/load.
- [ ] Faction reputation + guild-rank gated quest behavior smoke-tested.
- [ ] Prep-pack import checked for seeded quest/handout/encounter/POI content.

## E) Device checks

- [ ] Desktop/laptop checks completed.
- [ ] At least one phone-size player workflow tested.
- [ ] Layout/readability checked for common phone viewport issues.

## F) Admin and safety checks

- [ ] `DND_ADMIN_KEY` configured and verified.
- [ ] Password reset request flow tested.
- [ ] Password reset completion/admin reset flow tested.
- [ ] Backup completed before distribution.
- [ ] Restore notes reviewed and current.

## G) Release decision checkpoint

- [ ] All known Critical issues resolved or explicitly deferred with rationale.
- [ ] High-severity issues reviewed for workaround risk.
- [ ] Support/triage path is active and documented.
- [ ] Release owner signs off GO / NO-GO.
