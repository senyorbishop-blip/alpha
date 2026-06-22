import { test, expect } from '@playwright/test';
import { createIsolatedSession, expectNoRoleErrors, openRolePage } from './e2e-helpers';

test('Player quick-action shell renders without ReferenceError on live play page', async ({ browser, request }) => {
  const session = await createIsolatedSession(request, browser, 'quick-actions');
  const player = await openRolePage(browser, session, 'player');
  await player.page.locator('#rail-char-btn').click();
  await expect(player.page.locator('#flyout-char')).toBeVisible();
  await player.page.evaluate(() => {
    const fn = (window as any).__renderPlayerDashboardShell || (window as any).renderPlayerActionHub || (window as any).renderPlayerQuickActions;
    if (typeof fn === 'function') fn();
  });
  await expect(player.page.locator('#rail-dice-btn')).toBeVisible();
  await expectNoRoleErrors(player);
});
