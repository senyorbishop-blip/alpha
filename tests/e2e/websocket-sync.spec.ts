import { test, expect } from '@playwright/test';
import { createIsolatedSession, expectNoRoleErrors, openRolePage, waitForItemLibrarySync, waitForStateSync, waitForWsConnected } from './e2e-helpers';

test('all live roles receive initial WebSocket state and item library sync without heartbeat failures', async ({ browser, request }) => {
  const session = await createIsolatedSession(request, browser, 'ws-sync');
  const roles = [await openRolePage(browser, session, 'dm'), await openRolePage(browser, session, 'player'), await openRolePage(browser, session, 'viewer')];
  for (const role of roles) {
    await waitForWsConnected(role.page);
    await waitForStateSync(role.page);
    await waitForItemLibrarySync(role.page);
  }

  await expect.poll(async () => Promise.all(roles.map(r => r.page.evaluate(() => (window as any).__e2eWs?.errors || 0)))).toEqual([0, 0, 0]);
  await expect.poll(async () => Promise.all(roles.map(r => r.page.evaluate(() => ((window as any).__e2eWs?.closes || []).filter((c: any) => c.code !== 1000).length)))).toEqual([0, 0, 0]);
  await expectNoRoleErrors(...roles);
});
