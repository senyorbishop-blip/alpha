import { test, expect, type Locator, type Page } from '@playwright/test';
import { createIsolatedSession, expectNoRoleErrors, openRolePage } from './e2e-helpers';

type DmMode = 'run' | 'combat' | 'map-build' | 'npc-monster' | 'loot-shop' | 'session-tools' | 'viewer-powers' | 'debug';

const modeExpectations: Array<{ mode: DmMode; section: string; tool: string }> = [
  { mode: 'combat', section: 'combat', tool: 'initiative-order' },
  { mode: 'map-build', section: 'map-build', tool: 'terrain-tools' },
  { mode: 'npc-monster', section: 'npc-monster', tool: 'bestiary-search' },
  { mode: 'loot-shop', section: 'loot-shop', tool: 'item-search' },
  { mode: 'session-tools', section: 'session-tools', tool: 'quests' },
  { mode: 'viewer-powers', section: 'viewer-powers', tool: 'connected-viewers' },
];

function modeButton(page: Page, mode: DmMode): Locator {
  return page.locator(`[data-dm-mode-button="${mode}"]`);
}

function modeSection(page: Page, section: string): Locator {
  return page.locator(`[data-dm-context-section="${section}"], .dm-context-mode-panel[data-dm-mode="${section}"]`).first();
}

async function expectMapVisible(page: Page) {
  await expect(page.locator('[data-map-primary="true"]')).toBeVisible();
  await expect(page.locator('#map-canvas')).toBeVisible();
}

test('DM mode rail switches focused tool groups while keeping the map-first stage visible', async ({ browser, request }) => {
  const session = await createIsolatedSession(request, browser, 'dm-mode-ui');
  const dm = await openRolePage(browser, session, 'dm');

  await expect(dm.page.locator('#topbar-role')).toContainText(/DM/i);
  await expect(dm.page.locator('[data-dm-rail-shell="true"]')).toBeVisible();
  await expect(dm.page.locator('[data-dm-context-shell="true"]')).toBeVisible();

  await expect(modeButton(dm.page, 'run')).toHaveAttribute('aria-pressed', 'true');
  await expect(modeButton(dm.page, 'run')).toHaveAttribute('data-dm-mode-active', 'true');
  await expect(modeSection(dm.page, 'live-table')).toBeVisible();
  await expect(dm.page.locator('[data-dm-tool="selected-token-summary"]')).toBeVisible();
  await expect(dm.page.locator('[data-dm-debug-panel]')).toBeHidden();
  await expect(dm.page.locator('body')).not.toHaveAttribute('data-debug-open', 'true');
  await expectMapVisible(dm.page);

  for (const { mode, section, tool } of modeExpectations) {
    await modeButton(dm.page, mode).click();
    await expect(modeButton(dm.page, mode)).toHaveAttribute('aria-pressed', 'true');
    await expect(modeButton(dm.page, mode)).toHaveAttribute('data-dm-mode-active', 'true');
    await expect(modeSection(dm.page, section)).toBeVisible();
    await expect(dm.page.locator(`[data-dm-tool="${tool}"]`).first()).toBeVisible();
    await expectMapVisible(dm.page);
  }

  await modeButton(dm.page, 'debug').click();
  await expect(modeButton(dm.page, 'debug')).toHaveAttribute('aria-pressed', 'true');
  await expect(dm.page.locator('[data-dm-debug-panel]').first()).toBeVisible();
  await expect(dm.page.locator('body')).toHaveAttribute('data-debug-open', 'true');
  await expectMapVisible(dm.page);

  await expectNoRoleErrors(dm);
});

test('Player and Viewer do not receive the DM mode rail', async ({ browser, request }) => {
  const session = await createIsolatedSession(request, browser, 'dm-mode-role-separation');
  const player = await openRolePage(browser, session, 'player');
  const viewer = await openRolePage(browser, session, 'viewer');

  for (const role of [player, viewer]) {
    await expect(role.page.locator('[data-dm-rail-shell="true"]')).toBeHidden();
    await expect(role.page.locator('[data-dm-context-shell="true"]')).toBeHidden();
    await expect(role.page.locator('[data-dm-mode-button]')).toHaveCount(8);
    await expectMapVisible(role.page);
  }

  await expectNoRoleErrors(player, viewer);
});
