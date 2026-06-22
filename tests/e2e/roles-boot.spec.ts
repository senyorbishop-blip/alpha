import { test, expect } from '@playwright/test';
import { createIsolatedSession, expectNoRoleErrors, openRolePage, waitForItemLibrarySync } from './e2e-helpers';

test('DM, Player, and Viewer boot into role-appropriate live shells', async ({ browser, request }) => {
  const session = await createIsolatedSession(request, browser, 'roles-boot');
  const dm = await openRolePage(browser, session, 'dm');
  const player = await openRolePage(browser, session, 'player');
  const viewer = await openRolePage(browser, session, 'viewer');

  await waitForItemLibrarySync(player.page);

  await expect(dm.page.locator('#topbar-role')).toContainText(/DM/i);
  await expect(player.page.locator('#topbar-role')).toContainText(/Player/i);
  await expect(viewer.page.locator('#topbar-role')).toContainText(/Viewer/i);

  await expect(dm.page.locator('#rail-token-btn')).toBeVisible();
  await expect(dm.page.locator('#rail-editor-btn')).toBeVisible();
  await expect(dm.page.locator('#rail-fog-btn')).toBeVisible();

  await expect(player.page.locator('#rail-token-btn')).not.toBeVisible();
  await expect(player.page.locator('#rail-editor-btn')).not.toBeVisible();
  await expect(player.page.locator('#rail-fog-btn')).not.toBeVisible();
  await expect(player.page.locator('#rail-char-btn')).toBeVisible();

  await expect(viewer.page.locator('#rail-token-btn')).not.toBeVisible();
  await expect(viewer.page.locator('#rail-editor-btn')).not.toBeVisible();
  await expect(viewer.page.locator('#rail-fog-btn')).not.toBeVisible();
  await expect(viewer.page.locator('#rail-dice-btn')).toBeVisible();

  await expectNoRoleErrors(dm, player, viewer);
});
