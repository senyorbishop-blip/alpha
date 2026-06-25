import { test, expect } from '@playwright/test';
import path from 'node:path';

const ITEM_IMAGE_RESOLVER = path.join(process.cwd(), 'client/static/js/ui/item_image_resolver.js');
const ITEM_ROW = path.join(process.cwd(), 'client/static/js/ui/item_row.js');

async function loadItemRow(page: import('@playwright/test').Page) {
  await page.goto('about:blank');
  await page.addScriptTag({ path: ITEM_IMAGE_RESOLVER });
  await page.addScriptTag({ path: ITEM_ROW });
}

test.describe('item_row.js renderItemRow', () => {
  test('renders rarity chip and type · value line for each rarity', async ({ page }) => {
    await loadItemRow(page);

    const rarities = ['common', 'uncommon', 'rare', 'very rare', 'legendary'];
    for (const rarity of rarities) {
      const result = await page.evaluate((r) => {
        const item = { name: 'Test Widget', item_type: 'material', rarity: r, price_gp: 25 };
        const row = (window as any).ItemRow.renderItemRow(item, { mode: 'chest', qty: 1 });
        const chip = row.querySelector('.item-row-rarity');
        const secondary = row.querySelector('.item-row-secondary');
        return {
          chipText: chip ? chip.textContent : null,
          chipColor: chip ? chip.style.color : null,
          secondaryText: secondary ? secondary.textContent : null,
        };
      }, rarity);

      expect(result.chipText?.toLowerCase()).toBe(rarity);
      expect(result.chipColor).toBeTruthy();
      expect(result.chipColor).not.toBe('rgb(0, 0, 0)');
      expect(result.secondaryText).toBe('Material · 25 gp');
    }
  });

  test('buy mode dims the row and disables Buy when price exceeds gold', async ({ page }) => {
    await loadItemRow(page);

    const affordable = await page.evaluate(() => {
      const item = { name: 'Cheap Dagger', item_type: 'weapon', rarity: 'common', priceCp: 100 };
      const row = (window as any).ItemRow.renderItemRow(item, {
        mode: 'buy',
        gold: 500,
        buy: { onClick: "ShopView._buy('x')" },
      });
      const buyBtn = row.querySelector('button[onclick*="_buy"]');
      return {
        dimmed: row.classList.contains('item-row-dimmed'),
        buyDisabled: buyBtn ? buyBtn.hasAttribute('disabled') : null,
      };
    });
    expect(affordable.dimmed).toBe(false);
    expect(affordable.buyDisabled).toBe(false);

    const tooExpensive = await page.evaluate(() => {
      const item = { name: 'Fancy Sword', item_type: 'weapon', rarity: 'rare', priceCp: 1000 };
      const row = (window as any).ItemRow.renderItemRow(item, {
        mode: 'buy',
        gold: 100,
        buy: { onClick: "ShopView._buy('y')" },
      });
      const buyBtn = row.querySelector('button[onclick*="_buy"]');
      const note = row.querySelector('.item-row-need-note');
      return {
        dimmed: row.classList.contains('item-row-dimmed'),
        buyDisabled: buyBtn ? buyBtn.hasAttribute('disabled') : null,
        noteText: note ? note.textContent : null,
      };
    });
    expect(tooExpensive.dimmed).toBe(true);
    expect(tooExpensive.buyDisabled).toBe(true);
    expect(tooExpensive.noteText).toContain('Need');
  });

  test('chest mode preserves Take button onclick handlers', async ({ page }) => {
    await loadItemRow(page);

    const html = await page.evaluate(() => {
      const item = { name: 'Gold Ring', item_type: 'ring', rarity: 'uncommon', qty: 3 };
      const row = (window as any).ItemRow.renderItemRow(item, {
        mode: 'chest',
        qty: 3,
        takeOne: { onClick: 'ChestView._take(2, 1)' },
        takeAll: { onClick: 'ChestView._take(2, 3)' },
      });
      return row.outerHTML;
    });

    expect(html).toContain('onclick="ChestView._take(2, 1)"');
    expect(html).toContain('onclick="ChestView._take(2, 3)"');
  });
});
