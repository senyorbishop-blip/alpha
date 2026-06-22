import { test, expect } from '@playwright/test';
import { createIsolatedSession, currentTokens, expectNoRoleErrors, openRolePage, tokenByName, wsSend } from './e2e-helpers';

test('DM-created visible token syncs to Player and Viewer, and movement propagates', async ({ browser, request }) => {
  const session = await createIsolatedSession(request, browser, 'token-sync');
  const dm = await openRolePage(browser, session, 'dm');
  const player = await openRolePage(browser, session, 'player');
  const viewer = await openRolePage(browser, session, 'viewer');
  const name = `E2E Visible ${Date.now()}`;

  await wsSend(dm.page, { type: 'token_create', payload: { name, tokenType: 'npc', x: 160, y: 180, width: 40, height: 40, color: '#ff00aa', shape: 'circle', hidden: false, map_context: 'world' } });
  await expect.poll(() => tokenByName(dm.page, name)).not.toBeNull();
  await expect.poll(() => tokenByName(player.page, name)).not.toBeNull();
  await expect.poll(() => tokenByName(viewer.page, name)).not.toBeNull();

  const token = await tokenByName(dm.page, name);
  await wsSend(dm.page, { type: 'token_move', payload: { token_id: token.id, x: 300, y: 320 } });
  await expect.poll(async () => (await tokenByName(player.page, name))?.x).toBe(300);
  await expect.poll(async () => (await tokenByName(viewer.page, name))?.y).toBe(320);
  await expectNoRoleErrors(dm, player, viewer);
});

test('hidden NPCs disappear for Player and Viewer while remaining manageable by DM', async ({ browser, request }) => {
  const session = await createIsolatedSession(request, browser, 'hidden-npc');
  const dm = await openRolePage(browser, session, 'dm');
  const player = await openRolePage(browser, session, 'player');
  const viewer = await openRolePage(browser, session, 'viewer');
  const name = `E2E Hidden NPC ${Date.now()}`;

  await wsSend(dm.page, { type: 'token_create', payload: { name, tokenType: 'npc', x: 220, y: 220, width: 40, height: 40, color: '#aa2222', shape: 'circle', hidden: false, map_context: 'world' } });
  await expect.poll(() => tokenByName(player.page, name)).not.toBeNull();
  const token = await tokenByName(dm.page, name);

  await wsSend(dm.page, { type: 'toggle_hidden', payload: { token_id: token.id, hidden: true } });
  await expect.poll(() => tokenByName(dm.page, name)).not.toBeNull();
  await expect.poll(() => tokenByName(player.page, name)).toBeNull();
  await expect.poll(() => tokenByName(viewer.page, name)).toBeNull();

  const dmTokens = await currentTokens(dm.page);
  expect(dmTokens[token.id]?.hidden).toBeTruthy();
  await expectNoRoleErrors(dm, player, viewer);
});
