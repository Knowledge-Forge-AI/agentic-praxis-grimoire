import { test as base, expect } from '@playwright/test';
import path from 'node:path';
import { publishReadiness } from './supervisor_runner.mjs';

export const test = base.extend({
  serverOrigin: async ({}, use) => {
    const origin = process.env.APG_SERVER_ORIGIN || 'http://127.0.0.1:0';
    await use(origin);
  },
  supervisedPage: async ({ context, serverOrigin }, use) => {
    await context.route('**/*', (route) => {
      let parsed;
      try {
        parsed = new URL(route.request().url());
      } catch {
        return route.abort('blockedbyclient');
      }
      if (parsed.origin === serverOrigin && ['/', '/index.html', '/frame.html', '/popup.html', '/sprite.svg'].includes(parsed.pathname)) {
        route.continue();
      } else {
        route.abort('blockedbyclient');
      }
    });
    const page = await context.newPage();
    try { await use(page); } finally { await page.close(); }
  },
});

test.describe('Supervised Playwright Test Discovery and Fixtures', () => {
  test('supervisor-pass', async ({ supervisedPage, serverOrigin }) => {
    await supervisedPage.goto(`${serverOrigin}/index.html`, { waitUntil: 'domcontentloaded' });
    const btn = supervisedPage.locator('#single-btn');
    await expect(btn).toHaveText('Single Target');
  });

  test('supervisor-fail', async ({ supervisedPage, serverOrigin }) => {
    await supervisedPage.goto(`${serverOrigin}/index.html`, { waitUntil: 'domcontentloaded' });
    const btn = supervisedPage.locator('#single-btn');
    await expect(btn).toHaveText('CONTROLLED_FAILURE_INTENTIONAL_MISMATCH', { timeout: 1000 });
  });

  test('supervisor-interrupt', async ({ supervisedPage, serverOrigin }) => {
    const holdMs = Number(process.env.APG_INTERRUPT_HOLD_MS || 70000);
    if (!Number.isSafeInteger(holdMs) || holdMs <= 65000 || holdMs > 2147478647) {
      throw new Error('APG_INTERRUPT_HOLD_MS must exceed the 65000ms post-readiness safety bound');
    }
    test.setTimeout(holdMs + 5000);
    await supervisedPage.goto(`${serverOrigin}/index.html`, { waitUntil: 'domcontentloaded' });
    await expect(supervisedPage.locator('#single-btn')).toHaveText('Single Target');
    const signalPath = process.env.APG_SIGNAL_FILE;
    if (signalPath) {
      const browserName = process.env.APG_BROWSER_NAME;
      let browserExecutables;
      if (!browserName) throw new Error('Selected browser is missing from interruption environment');
      try { browserExecutables = JSON.parse(process.env.APG_BROWSER_EXECUTABLES); }
      catch { throw new Error('Selected browser executable facts are missing from interruption environment'); }
      if (!Array.isArray(browserExecutables) || !browserExecutables.length ||
          browserExecutables.some(executable => typeof executable !== 'string' || !path.isAbsolute(executable))) {
        throw new Error('Selected browser executable facts are invalid');
      }
      publishReadiness(signalPath, { pid: process.pid, browserName, browserExecutables });
    }
    console.log(`READY_FOR_INTERRUPT pid=${process.pid} browser=${process.env.APG_BROWSER_NAME || 'unknown'}`);
    await new Promise((resolve) => setTimeout(resolve, holdMs));
  });
});
