import { expect, type APIRequestContext, type Browser, type BrowserContext, type Page } from '@playwright/test';

export type RoleName = 'dm' | 'player' | 'viewer';
export type RolePage = { role: RoleName; context: BrowserContext; page: Page; userId: string; name: string; errors: string[] };
export type TestSession = { sessionId: string; dmUserId: string; playerUserId: string; viewerUserId: string; playerInvite: string; viewerInvite: string };

const criticalConsole = /\b(ReferenceError|SyntaxError|TypeError:|Uncaught|Failed to load resource: the server responded with a status of (?:4|5)\d\d)\b/i;
const harmless = [/favicon\.ico/i, /ResizeObserver loop/i];

export async function registerUser(request: APIRequestContext, role: RoleName, prefix: string) {
  const unique = `${prefix}-${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const res = await request.post('/api/auth/register', {
    data: { username: unique, email: `${unique}@e2e.invalid`, password: 'playwright-pass', role },
  });
  expect(res.ok(), `${role} registration should succeed: ${await res.text()}`).toBeTruthy();
  const body = await res.json();
  return { username: unique, user: body.user, token: body.token as string };
}

export async function createIsolatedSession(request: APIRequestContext, browser: Browser, prefix = 'e2e'): Promise<TestSession> {
  const dmAuth = await registerUser(request, 'dm', prefix);
  const create = await request.post('/api/session/create', {
    headers: { Authorization: `Bearer ${dmAuth.token}` },
    data: { dm_name: 'E2E Dungeon Master', campaign_name: `E2E ${Date.now()}` },
  });
  expect(create.ok(), `session create should succeed: ${await create.text()}`).toBeTruthy();
  const created = await create.json();

  async function join(role: 'player' | 'viewer', invite: string) {
    const auth = await registerUser(request, role, prefix);
    const res = await request.post('/api/session/join', {
      headers: { Authorization: `Bearer ${auth.token}` },
      data: { session_id: created.session_id, invite_code: invite },
    });
    expect(res.ok(), `${role} join should succeed: ${await res.text()}`).toBeTruthy();
    const joined = await res.json();
    return joined.user_id as string;
  }

  const playerUserId = await join('player', created.player_invite);
  const viewerUserId = await join('viewer', created.viewer_invite);
  return { sessionId: created.session_id, dmUserId: created.user_id, playerUserId, viewerUserId, playerInvite: created.player_invite, viewerInvite: created.viewer_invite };
}

export async function openRolePage(browser: Browser, session: TestSession, role: RoleName): Promise<RolePage> {
  const context = await browser.newContext();
  const page = await context.newPage();
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(`[pageerror] ${e.message}`));
  page.on('console', msg => {
    const text = msg.text();
    if ((msg.type() === 'error' || criticalConsole.test(text)) && !harmless.some(r => r.test(text))) errors.push(`[console:${msg.type()}] ${text}`);
  });
  page.on('requestfailed', req => {
    if (['document', 'script', 'xhr', 'fetch', 'websocket'].includes(req.resourceType())) errors.push(`[requestfailed] ${req.method()} ${req.url()} ${req.failure()?.errorText}`);
  });
  await page.addInitScript(() => {
    (window as any).__e2eMessages = [];
    (window as any).__e2eWs = { opens: 0, closes: [], errors: 0 };
    const NativeWS = window.WebSocket;
    class E2EWebSocket extends NativeWS {
      constructor(url: string | URL, protocols?: string | string[]) {
        super(url, protocols as any);
        this.addEventListener('open', () => { (window as any).__e2eWs.opens += 1; });
        this.addEventListener('close', (ev) => { (window as any).__e2eWs.closes.push({ code: ev.code, reason: ev.reason }); });
        this.addEventListener('error', () => { (window as any).__e2eWs.errors += 1; });
        this.addEventListener('message', (ev) => {
          try { (window as any).__e2eMessages.push(JSON.parse(String(ev.data))); } catch { /* ignore non-json */ }
        });
      }
    }
    (window as any).WebSocket = E2EWebSocket as any;
  });
  const userId = role === 'dm' ? session.dmUserId : role === 'player' ? session.playerUserId : session.viewerUserId;
  await page.goto(`/play?session_id=${session.sessionId}&user_id=${userId}&role=${role}`);
  await waitForStateSync(page);
  return { role, context, page, userId, name: role, errors };
}

export async function waitForWsConnected(page: Page) {
  await expect.poll(() => page.evaluate(() => (window as any).__e2eWs?.opens || 0), { message: 'WebSocket opens' }).toBeGreaterThan(0);
  await expect(page.locator('#ws-status-label')).toContainText(/Connected|Live|Online|Sync|Ready/i, { timeout: 20_000 }).catch(() => undefined);
}

export async function waitForStateSync(page: Page) {
  await waitForWsConnected(page);
  await expect.poll(() => page.evaluate(() => (window as any).__e2eMessages?.some((m: any) => m.type === 'state_sync')), { message: 'state_sync received' }).toBeTruthy();
}

export async function waitForItemLibrarySync(page: Page) {
  await expect.poll(() => page.evaluate(() => (window as any).__e2eMessages?.some((m: any) => m.type === 'item_library_sync')), { message: 'item_library_sync received' }).toBeTruthy();
}

export async function wsSend(page: Page, msg: unknown) {
  await page.evaluate((payload) => (window as any).sendWS(payload), msg);
}

export async function currentTokens(page: Page): Promise<Record<string, any>> {
  return page.evaluate(() => ({ ...(window as any).tokens }));
}

export async function tokenByName(page: Page, name: string): Promise<any | null> {
  return page.evaluate((tokenName) => Object.values((window as any).tokens || {}).find((t: any) => t?.name === tokenName) || null, name);
}

export async function expectNoRoleErrors(...roles: RolePage[]) {
  for (const role of roles) expect(role.errors, `${role.role} browser errors`).toEqual([]);
}
