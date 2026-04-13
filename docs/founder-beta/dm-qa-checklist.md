# DM QA Checklist (Founder Beta)

Run this from a DM perspective on at least one desktop browser. Repeat core items on a second browser profile when possible.

## 1) Install/startup and login

- [ ] Install from docs succeeds.
- [ ] Server starts without blocking errors.
- [ ] DM login/entry succeeds.

## 2) Session and invite flow

- [ ] DM can create or enter session.
- [ ] Session ID/invite codes are visible and usable.
- [ ] Player can join using DM-provided info.

## 3) Map load/upload/editor flow

- [ ] Map loads from existing library.
- [ ] Upload/import path works for a test asset/map.
- [ ] Basic editor actions work (paint/place/select/remove).
- [ ] Changes remain visible after refresh/reopen.

## 4) Fog and visibility

- [ ] Fog mode switches correctly.
- [ ] Reveal/hide tools apply as expected.
- [ ] Player-side visibility reflects DM fog actions.

## 5) Walls/doors and map interaction

- [ ] Walls can be created/edited/removed.
- [ ] Doors/open-closed states work as expected.
- [ ] Navigation/line-of-sight behavior remains usable.

## 6) Combat and initiative

- [ ] Combat can start and end cleanly.
- [ ] Initiative order is readable and usable.
- [ ] Turn progression is visible to relevant roles.

## 7) Token/object control

- [ ] Token/object quick panel opens reliably.
- [ ] DM can update key token fields used in play.
- [ ] Ownership/permission behavior is correct.

## 8) Prep mode vs live play mode

- [ ] Prep/edit actions are available in prep flow.
- [ ] Live play flow does not expose unintended DM-only controls to players.

## 9) Save/load and reconnect

- [ ] Save writes expected state.
- [ ] Load restores expected state.
- [ ] Reconnect after DM refresh resumes session control.

## 10) Device checks

- [ ] Core DM flow validated on desktop/laptop.
- [ ] Quick sanity check on tablet (if part of target usage).
- [ ] Phone check performed for emergency/quick admin view only.
