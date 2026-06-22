import { test, expect } from '@playwright/test';
import { createIsolatedSession, expectNoRoleErrors, openRolePage, wsSend } from './e2e-helpers';

test('Viewer cannot perform restricted token creation over the live WebSocket', async ({ browser, request }) => {
  const session = await createIsolatedSession(request, browser, 'viewer-perms');
  const viewer = await openRolePage(browser, session, 'viewer');
  await wsSend(viewer.page, { type: 'token_create', payload: { name: 'Viewer Forbidden Token', x: 10, y: 10 } });
  await expect.poll(() => viewer.page.evaluate(() => Object.values((window as any).tokens || {}).some((t: any) => t?.name === 'Viewer Forbidden Token'))).toBeFalsy();
  await expectNoRoleErrors(viewer);
});
