import { test, expect, type Page } from '@playwright/test';
import { createIsolatedSession, openRolePage, wsSend, type RolePage } from './e2e-helpers';

// Assert the token-edit flow raised no uncaught JS exceptions. We intentionally
// look only at [pageerror] entries: console resource 404s come from optional
// third-party CDN assets (three.js / cannon-es for 3D dice) that sandboxed
// network policies block, and are unrelated to token-edit permissions.
function expectNoUncaughtErrors(...roles: RolePage[]) {
  for (const role of roles) {
    const pageErrors = role.errors.filter(e => e.startsWith('[pageerror]'));
    expect(pageErrors, `${role.role} uncaught errors`).toEqual([]);
  }
}

// Repro for: "I cannot edit tokens as dm and players cannot edit their own".
//
// The token editor is reachable from the right-click context menu (#ctx-edit-token)
// and, for the DM, from the selected-token quick panel. The bug: the context-menu
// "Edit Token" item was gated to ROLE === 'dm', so a player could never edit the
// token they own even though the server authorises owner edits.

const TOKEN_W = 40;
const TOKEN_X = 300;
const TOKEN_Y = 300;
const CENTER_X = TOKEN_X + TOKEN_W / 2;
const CENTER_Y = TOKEN_Y + TOKEN_W / 2;

// Wait until the app's real token store (a module-scoped binding, not window.tokens)
// has rendered the token, using the global hitTestTokens() helper.
async function waitForTokenHit(page: Page) {
  await expect
    .poll(() => page.evaluate(([cx, cy]) => {
      const fn = (window as any).hitTestTokens;
      return typeof fn === 'function' && !!fn(cx, cy);
    }, [CENTER_X, CENTER_Y]), { message: 'token hit-testable', timeout: 20_000 })
    .toBeTruthy();
}

// Convert a world point to viewport client coordinates for a real mouse event.
async function worldToClient(page: Page): Promise<{ clientX: number; clientY: number }> {
  return page.evaluate(([wx, wy]) => {
    const canvas = document.getElementById('map-canvas') as HTMLCanvasElement;
    const rect = canvas.getBoundingClientRect();
    const s = (window as any).worldToScreen(wx, wy); // canvas-internal pixels
    return {
      clientX: rect.left + s.x * (rect.width / Math.max(1, canvas.width)),
      clientY: rect.top + s.y * (rect.height / Math.max(1, canvas.height)),
    };
  }, [CENTER_X, CENTER_Y]);
}

async function editTokenMenuVisible(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const el = document.getElementById('ctx-edit-token');
    return !!el && el.style.display !== 'none' && getComputedStyle(el).display !== 'none';
  });
}

async function editorModalOpen(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const el = document.getElementById('token-editor');
    return !!el && getComputedStyle(el).display !== 'none';
  });
}

function fieldVisible(page: Page, id: string): Promise<boolean> {
  return page.evaluate((elId) => {
    const el = document.getElementById(elId);
    return !!el && getComputedStyle(el).display !== 'none' && el.offsetParent !== null;
  }, id);
}

async function rightClickTokenAndEdit(page: Page, label: string, role: 'dm' | 'player') {
  await waitForTokenHit(page);
  const { clientX, clientY } = await worldToClient(page);
  // Drive the real right-click handler (the app calls it the same way for long-press).
  await page.evaluate(([cx, cy]) => {
    (window as any).onRightClick({ preventDefault() {}, clientX: cx, clientY: cy, button: 2 });
  }, [clientX, clientY]);
  expect(await editTokenMenuVisible(page), `${label} should see "Edit Token" in the context menu`).toBeTruthy();
  // Trigger the menu item's wired action (onclick="openTokenEditor()"). onRightClick
  // has already set the module-scoped ctxToken to the right-clicked token.
  await page.evaluate(() => (window as any).openTokenEditor());
  // Modal must be genuinely visible — not just inline display:block but actually
  // computed-visible (the DM map-first CSS used to force display:none !important).
  expect(await editorModalOpen(page), `${label} token editor modal should be visible`).toBeTruthy();

  // Owner-editable fields are visible to everyone who can open the editor.
  expect(await fieldVisible(page, 'te-ac'), `${label} should see the AC field`).toBeTruthy();
  // DM-only fields (name) are visible to the DM but hidden from a player owner.
  expect(await fieldVisible(page, 'te-name'), `${label} name field visibility`).toBe(role === 'dm');

  // Close it before the next role so state is clean.
  await page.evaluate(() => (window as any).closeTokenEditor && (window as any).closeTokenEditor());
}

test('DM and owning player can reach the token editor via the context menu', async ({ browser, request }) => {
  const session = await createIsolatedSession(request, browser, 'token-edit-perms');
  const dm = await openRolePage(browser, session, 'dm');
  const player = await openRolePage(browser, session, 'player');

  // DM creates a token owned by the player.
  await wsSend(dm.page, {
    type: 'token_create',
    payload: {
      name: 'Elphaba', owner_id: session.playerUserId,
      x: TOKEN_X, y: TOKEN_Y, width: TOKEN_W, height: TOKEN_W,
      color: '#3498db', shape: 'circle', hp: 67, maxHp: 67, ac: 15,
      tokenType: 'player', map_context: 'world', hidden: false,
    },
  });

  await rightClickTokenAndEdit(dm.page, 'DM', 'dm');
  await rightClickTokenAndEdit(player.page, 'Owning player', 'player');

  expectNoUncaughtErrors(dm, player);
});
