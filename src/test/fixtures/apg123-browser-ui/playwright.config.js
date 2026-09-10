import { defineConfig } from '@playwright/test';

export default defineConfig({
  testMatch: 'supervisor.spec.js',
  retries: 0,
  workers: 1,
  outputDir: 'test-results',
  use: {
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    serviceWorkers: 'block',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
    {
      name: 'firefox',
      use: { browserName: 'firefox' },
    },
    {
      name: 'webkit',
      use: { browserName: 'webkit' },
    },
  ],
});
