import { test, expect } from '@playwright/test';
import { createIsolatedSession, openRolePage } from './e2e-helpers';

test.describe('chest contents render via ItemRow', () => {
  test('chest list shows rarity chip and keeps Take button handlers', async ({ browser, request }) => {
    const session = await createIsolatedSession(request, browser, 'chest');
    const player = await openRolePage(browser, session, 'player');

    const html = await player.page.evaluate(() => {
      (window as any).ChestView.open(
        {
          id: 'chest-1',
          name: 'Treasure Chest',
          kind: 'chest',
          slot_count: 12,
          inventory: [
            { name: 'Gold Ring', item_type: 'ring', rarity: 'uncommon', qty: 3 },
            { name: 'Ancient Tome', item_type: 'wondrous item', rarity: 'legendary', qty: 1, is_magic: true },
          ],
        },
        'player',
      );
      const modal = document.getElementById('dnd-chest-view');
      return modal ? modal.innerHTML : '';
    });

    expect(html).toContain('item-row-rarity');
    expect(html).toContain('ChestView._take(0, 1)');
    expect(html).toContain('ChestView._take(0, 3)');
    expect(html).toContain('ChestView._take(1, 1)');
    expect(html).toContain('cv-badge-magic');

    await player.page.evaluate(() => (window as any).ChestView.close());
  });
});
