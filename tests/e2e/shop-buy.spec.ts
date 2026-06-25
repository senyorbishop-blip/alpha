import { test, expect } from '@playwright/test';
import { createIsolatedSession, openRolePage } from './e2e-helpers';

test.describe('shop buy/sell rows render via ItemRow', () => {
  test('buy list shows rarity chip, dims unaffordable items, and keeps Buy handlers', async ({ browser, request }) => {
    const session = await createIsolatedSession(request, browser, 'shop-buy');
    const player = await openRolePage(browser, session, 'player');

    const html = await player.page.evaluate(() => {
      (window as any).ShopView.open(
        {
          id: 'shop-1',
          name: 'Test Shop',
          shopkeeper_name: 'Gruff',
          shop_type: 'general',
          inventory: [
            { id: 'affordable-item', name: 'Cheap Dagger', item_type: 'weapon', rarity: 'common', price_gp: 5, quantity: 3 },
            { id: 'pricey-item', name: 'Fancy Sword', item_type: 'weapon', rarity: 'rare', price_gp: 9999, quantity: 1 },
          ],
        },
        1000,
        {},
        {},
        {},
        {},
      );
      const modal = document.getElementById('dnd-shop-view');
      return modal ? modal.innerHTML : '';
    });

    expect(html).toContain('item-row-rarity');
    expect(html).toContain("ShopView._buy('affordable-item')");
    expect(html).toContain("ShopView._buy('pricey-item')");

    const rows = await player.page.evaluate(() => {
      const affordableBtn = document.querySelector('button[onclick*="affordable-item"]');
      const pricBtn = document.querySelector('button[onclick*="pricey-item"]');
      const pricRow = pricBtn ? pricBtn.closest('.item-row') : null;
      return {
        affordableDisabled: affordableBtn ? affordableBtn.hasAttribute('disabled') : null,
        priceyDisabled: pricBtn ? pricBtn.hasAttribute('disabled') : null,
        priceyDimmed: pricRow ? pricRow.classList.contains('item-row-dimmed') : null,
      };
    });
    expect(rows.affordableDisabled).toBe(false);
    expect(rows.priceyDisabled).toBe(true);
    expect(rows.priceyDimmed).toBe(true);

    await player.page.evaluate(() => (window as any).ShopView.close());
  });
});
