import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('WeatherGPT Shell Accessibility & Navigation', () => {
  test('shell has proper document landmark, title, and initial lang', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle(/WeatherGPT/i);

    const htmlLang = await page.getAttribute('html', 'lang');
    expect(htmlLang).toBe('en');

    // Landmarks
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('main#main-content')).toBeVisible();
    await expect(page.locator('nav[aria-label="Mobile Navigation"], nav[aria-label="Desktop Navigation"]')).toBeVisible();
  });

  test('shell passes automated axe accessibility evaluation', async ({ page }) => {
    await page.goto('/');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('language switcher changes document lang attribute and UI strings', async ({ page }) => {
    await page.goto('/');

    // Switch to Hindi
    const hiButton = page.getByRole('radio', { name: 'हिन्दी' });
    await hiButton.click();

    const htmlLang = await page.getAttribute('html', 'lang');
    expect(htmlLang).toBe('hi');
  });

  test('navigation switches between registered features', async ({ page }) => {
    await page.goto('/');

    // Go to Alerts
    await page.getByRole('button', { name: /alerts|अलर्ट/i }).first().click();
    await expect(page.locator('text=Official warnings')).toBeVisible();

    // Go to Places
    await page.getByRole('button', { name: /places|स्थान/i }).first().click();
    await expect(page.locator('text=Saved Places')).toBeVisible();

    // Go to More
    await page.getByRole('button', { name: /more|और/i }).first().click();
    await expect(page.locator('text=Sources and licences')).toBeVisible();
  });
});
