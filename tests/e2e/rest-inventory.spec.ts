import { test, expect } from '@playwright/test';
import { createIsolatedSession, expectNoRoleErrors, openRolePage, tokenByName, wsSend } from './e2e-helpers';

test('DM-triggered long rest restores player token HP and clears temp HP across browsers', async ({ browser, request }) => {
  const session = await createIsolatedSession(request, browser, 'long-rest');
  const dm = await openRolePage(browser, session, 'dm');
  const player = await openRolePage(browser, session, 'player');
  const name = `E2E Rest Hero ${Date.now()}`;

  await wsSend(dm.page, { type: 'token_create', payload: { name, owner_id: session.playerUserId, tokenType: 'player', x: 120, y: 120, width: 40, height: 40, hp: 3, maxHp: 20, tempHp: 5, color: '#44aaff', shape: 'circle', map_context: 'world' } });
  await expect.poll(() => tokenByName(player.page, name)).not.toBeNull();
  const token = await tokenByName(dm.page, name);
  await wsSend(dm.page, { type: 'camp_rest_take_rest', payload: { rest_type: 'long' } });

  await expect.poll(async () => (await tokenByName(player.page, name))?.hp).toBe(20);
  await expect.poll(async () => (await tokenByName(dm.page, name))?.hp).toBe(20);
  await expect.poll(async () => (await tokenByName(player.page, name))?.temp_hp ?? 0).toBe(0);
  expect(token.id).toBeTruthy();
  await expectNoRoleErrors(dm, player);
});
