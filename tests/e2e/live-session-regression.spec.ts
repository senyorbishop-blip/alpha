import { expect, test, type Page } from '@playwright/test';
import {
  createIsolatedSession,
  currentTokens,
  openRolePage,
  tokenByName,
  waitForItemLibrarySync,
  wsSend,
  type RolePage,
} from './e2e-helpers';

const PLAYER_TOKEN = 'E2E Bishop';
const HIDDEN_NPC = 'E2E Hidden Guard';

async function waitForWsMessage(page: Page, type: string, text?: string) {
  await page.waitForFunction(
    ({ messageType, containsText }) => {
      const messages = (window as any).__e2eMessages || [];
      return messages.some((m: any) => {
        if (!m || m.type !== messageType) return false;
        if (!containsText) return true;
        try { return JSON.stringify(m).includes(containsText); } catch { return false; }
      });
    },
    { messageType: type, containsText: text || '' },
    { timeout: 20_000 },
  );
}

async function waitForToken(page: Page, name: string) {
  await expect.poll(async () => Boolean(await tokenByName(page, name)), {
    message: `token ${name} should be visible`,
    timeout: 20_000,
  }).toBeTruthy();
  return tokenByName(page, name);
}

async function expectTokenHiddenFrom(page: Page, name: string) {
  await expect.poll(async () => Boolean(await tokenByName(page, name)), {
    message: `token ${name} should stay hidden from this role`,
    timeout: 10_000,
  }).toBeFalsy();
}

async function combatState(page: Page) {
  return page.evaluate(() => (window as any)._combat || (window as any).combatState || null);
}

async function expectNoRuntimeErrors(...roles: RolePage[]) {
  const runtimeError = /(ReferenceError|SyntaxError|TypeError:|Uncaught|Message dispatch)/i;
  for (const role of roles) {
    const fatal = role.errors.filter((entry) => runtimeError.test(entry));
    expect(fatal, `${role.role} runtime errors`).toEqual([]);
  }
}

test.describe('live DM/player/viewer session regression', () => {
  test('keeps hidden tokens filtered while combat, movement, rest, reconnect, and viewer powers sync', async ({ request, browser }) => {
    const session = await createIsolatedSession(request, browser, 'live-regression');
    const dm = await openRolePage(browser, session, 'dm');
    const player = await openRolePage(browser, session, 'player');
    const viewer = await openRolePage(browser, session, 'viewer');

    await Promise.all([
      waitForItemLibrarySync(dm.page),
      waitForItemLibrarySync(player.page),
      waitForItemLibrarySync(viewer.page),
    ]);

    // DM places the player token and a hidden NPC. The player token must appear
    // to player/DM, while the hidden NPC must never appear to player/viewer.
    await wsSend(dm.page, {
      type: 'token_create',
      payload: {
        name: PLAYER_TOKEN,
        owner_id: session.playerUserId,
        tokenType: 'player',
        token_type: 'player',
        x: 100,
        y: 100,
        width: 40,
        height: 40,
        hp: 8,
        maxHp: 20,
        ac: 15,
        speed: 30,
        map_context: 'world',
        color: '#4ade80',
      },
    });

    const playerToken = await waitForToken(player.page, PLAYER_TOKEN);
    await waitForToken(dm.page, PLAYER_TOKEN);

    await wsSend(dm.page, {
      type: 'token_create',
      payload: {
        name: HIDDEN_NPC,
        tokenType: 'npc',
        token_type: 'npc',
        x: 220,
        y: 100,
        width: 40,
        height: 40,
        hp: 13,
        maxHp: 13,
        ac: 13,
        speed: 30,
        map_context: 'world',
        hidden: true,
        color: '#ef4444',
      },
    });

    const hiddenNpc = await waitForToken(dm.page, HIDDEN_NPC);
    await expectTokenHiddenFrom(player.page, HIDDEN_NPC);
    await expectTokenHiddenFrom(viewer.page, HIDDEN_NPC);

    const hiddenLeak = await viewer.page.evaluate((npcName) => {
      const messages = (window as any).__e2eMessages || [];
      return messages.some((m: any) => {
        try { return JSON.stringify(m).includes(npcName); } catch { return false; }
      });
    }, HIDDEN_NPC);
    expect(hiddenLeak, 'viewer websocket payloads must not include hidden NPC names').toBeFalsy();

    // Start combat with the visible player token and hidden guard. Player should
    // receive an authoritative combat state without the hidden guard leaking.
    await wsSend(dm.page, {
      type: 'combat_update',
      payload: {
        active: true,
        turn: 0,
        round: 1,
        combatants: [
          {
            id: 'e2e-player-combatant',
            token_id: playerToken.id,
            name: PLAYER_TOKEN,
            initiative: null,
            modifier: 2,
            is_player: true,
            owner_id: session.playerUserId,
            hp: 8,
            max_hp: 20,
            ac: 15,
            speed: 30,
          },
          {
            id: 'e2e-hidden-guard-combatant',
            token_id: hiddenNpc.id,
            name: HIDDEN_NPC,
            initiative: null,
            modifier: 1,
            is_player: false,
            hp: 13,
            max_hp: 13,
            ac: 13,
            speed: 30,
          },
        ],
      },
    });

    await expect.poll(async () => Boolean((await combatState(player.page))?.active), {
      message: 'player combat state should become active',
      timeout: 20_000,
    }).toBeTruthy();

    const playerCombatNames = await player.page.evaluate(() => ((window as any)._combat?.combatants || []).map((c: any) => c.name));
    expect(playerCombatNames).toContain(PLAYER_TOKEN);
    expect(playerCombatNames).not.toContain(HIDDEN_NPC);

    // Player rolls initiative and moves their own active token. This catches
    // combat_state, combat_initiative_rolled, dice_result, token_move, and
    // combat movement sync regressions in one flow.
    await wsSend(player.page, {
      type: 'combat_roll_initiative',
      payload: { token_id: playerToken.id, roll: 12, modifier: 2, roll_id: 'e2e-init-player' },
    });

    await expect.poll(async () => {
      const state = await combatState(player.page);
      const row = (state?.combatants || []).find((c: any) => c.token_id === playerToken.id);
      return row?.initiative;
    }, { message: 'player initiative should sync', timeout: 20_000 }).toBe(14);

    await wsSend(player.page, {
      type: 'token_move',
      payload: { token_id: playerToken.id, x: 140, y: 100, client_action_id: 'e2e-move-player' },
    });

    await expect.poll(async () => Number((await tokenByName(dm.page, PLAYER_TOKEN))?.x), {
      message: 'DM should see player token movement',
      timeout: 20_000,
    }).toBe(140);

    // Quick Actions should at least hydrate their bridge/runtime without throwing.
    // Dedicated unit tests cover exact weapon/spell picker math; this e2e catches
    // missing script/runtime regressions after reconnect/live-state sync.
    const quickActionRuntime = await player.page.evaluate(() => ({
      hasQuickActions: !!(window as any).CombatQuickActions,
      hasQuickBar: !!(window as any).CombatQuickBar || typeof (window as any).getCombatQuickBarRuntime === 'function',
      weaponCards: typeof (window as any)._getUnifiedQuickAttackCards === 'function'
        ? ((window as any)._getUnifiedQuickAttackCards() || []).length
        : null,
      spellCards: typeof (window as any).getCombatQuickBarSpells === 'function'
        ? ((window as any).getCombatQuickBarSpells() || []).length
        : null,
    }));
    expect(quickActionRuntime.hasQuickActions, 'CombatQuickActions runtime should load').toBeTruthy();

    // DM long rest should restore the damaged player token and broadcast rest,
    // token, character, inventory, and quick action sync events.
    await wsSend(dm.page, { type: 'camp_rest_take_rest', payload: { rest_type: 'long' } });
    await waitForWsMessage(player.page, 'camp_rest_rest_applied', 'long');
    await waitForWsMessage(player.page, 'quick_actions_sync');

    await expect.poll(async () => Number((await tokenByName(player.page, PLAYER_TOKEN))?.hp), {
      message: 'long rest should restore player token HP',
      timeout: 20_000,
    }).toBe(20);

    // Reconnect the player and ensure the restored state and Quick Actions still
    // hydrate from server state.
    const reconnectedPlayer = await openRolePage(browser, session, 'player');
    await waitForWsMessage(reconnectedPlayer.page, 'quick_actions_sync');
    await expect.poll(async () => Number((await tokenByName(reconnectedPlayer.page, PLAYER_TOKEN))?.hp), {
      message: 'reconnected player should see restored HP',
      timeout: 20_000,
    }).toBe(20);
    await expectTokenHiddenFrom(reconnectedPlayer.page, HIDDEN_NPC);

    // Viewer powers: DM grants a direct power, viewer uses it on the visible
    // player token, and all clients receive the FX/status without hidden leaks.
    await wsSend(dm.page, {
      type: 'viewer_power_grant',
      payload: {
        viewer_user_id: session.viewerUserId,
        power_id: 'arcane_zap',
        charges: 1,
        requires_approval: false,
        cooldown_sec: 0,
      },
    });
    await waitForWsMessage(viewer.page, 'viewer_profiles_sync', 'arcane_zap');

    await wsSend(viewer.page, {
      type: 'viewer_power_use',
      payload: { power_id: 'arcane_zap', target: { token_id: playerToken.id } },
    });
    await waitForWsMessage(viewer.page, 'viewer_power_status', 'used');
    await waitForWsMessage(dm.page, 'viewer_power_fx', 'arcane_zap');

    const viewerHiddenLeakAfterPower = await viewer.page.evaluate((npcName) => {
      const messages = (window as any).__e2eMessages || [];
      return messages.some((m: any) => {
        try { return JSON.stringify(m).includes(npcName); } catch { return false; }
      });
    }, HIDDEN_NPC);
    expect(viewerHiddenLeakAfterPower, 'viewer payloads must still not include hidden NPC after power flow').toBeFalsy();

    await expectNoRuntimeErrors(dm, player, viewer, reconnectedPlayer);

    await Promise.all([
      dm.context.close(),
      player.context.close(),
      viewer.context.close(),
      reconnectedPlayer.context.close(),
    ]);
  });
});
