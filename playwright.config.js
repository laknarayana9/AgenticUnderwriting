const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './browser-tests',
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:8000',
    headless: true,
  },
});
