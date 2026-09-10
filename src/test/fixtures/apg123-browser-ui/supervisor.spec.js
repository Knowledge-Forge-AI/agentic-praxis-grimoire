import { test as base, expect } from '@playwright/test';
import fs from 'node:fs';

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
    await supervisedPage.goto(`${serverOrigin}/index.html`, { waitUntil: 'domcontentloaded' });
    await expect(supervisedPage.locator('#single-btn')).toHaveText('Single Target');
    const signalPath = process.env.APG_SIGNAL_FILE;
    if (signalPath) {
      fs.writeFileSync(signalPath, 'READY\n');
    }
    console.log('READY_FOR_INTERRUPT');
    await new Promise((resolve) => setTimeout(resolve, 60000));
  });
});
