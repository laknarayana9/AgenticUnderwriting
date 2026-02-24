const { test, expect } = require('@playwright/test');

async function submitAgenticQuote(page, { address, coverage }) {
  // Open the main index page served by FastAPI
  await page.goto('http://localhost:8000/static/index.html');

  // Fill in property address and coverage amount
  await page.fill('#address', address);
  await page.fill('#coverage_amount', coverage.toString());

  // Ensure Agentic behavior is enabled
  const agenticCheckbox = page.locator('#use_agentic');
  if (!(await agenticCheckbox.isChecked())) {
    await agenticCheckbox.check();
  }

  // For deterministic testing, disable async queue so we hit /quote/run directly
  const queueCheckbox = page.locator('#use_queue');
  if (await queueCheckbox.isChecked()) {
    await queueCheckbox.uncheck();
  }

  // Submit the quote
  await page.click('button[type="submit"]');

  // Wait for underwriting decision to appear
  const decisionTitle = page.locator('#decisionContent span.text-2xl.font-bold');

  await expect(decisionTitle).toBeVisible({ timeout: 60_000 });

  // Verify we received some decision text (ACCEPT/REFER/REJECT/UNKNOWN)
  const decisionText = (await decisionTitle.textContent())?.trim();
  console.log(`Decision for coverage ${coverage}: ${decisionText}`);
  expect(decisionText).not.toBe('');
}

test.describe('Agentic Quote UI - index.html', () => {
  test('Agentic quote for coverage 500000', async ({ page }) => {
    await submitAgenticQuote(page, {
      address: '500 Elm St, Irvine, CA 92620',
      coverage: 500000,
    });
  });

  test('Agentic quote for coverage 600000', async ({ page }) => {
    await submitAgenticQuote(page, {
      address: '600 Oak Ave, Irvine, CA 92620',
      coverage: 600000,
    });
  });

  test('Agentic quote for coverage 700000', async ({ page }) => {
    await submitAgenticQuote(page, {
      address: '700 Pine Rd, Irvine, CA 92620',
      coverage: 700000,
    });
  });
});
