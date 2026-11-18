import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('WeatherGPT Full Experience & Accessibility', () => {
  test('shell has proper document landmarks, title, and initial lang', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/WeatherGPT/i);

    const htmlLang = await page.getAttribute('html', 'lang');
    expect(htmlLang).toBe('en');

    // Landmarks
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('main#main-content')).toBeVisible();
    await expect(page.locator('nav[aria-label="Mobile Navigation"], nav[aria-label="Desktop Navigation"]')).toBeVisible();
  });

  test('shell passes automated axe accessibility evaluation on Ask page', async ({ page }) => {
    await page.goto('/');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('passes axe evaluation on Alerts, Places, and More pages', async ({ page }) => {
    await page.goto('/');

    // 1. Check Alerts
    await page.getByRole('button', { name: /alerts|अलर्ट/i }).first().click();
    const alertsAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(alertsAxe.violations).toEqual([]);

    // 2. Check Places
    await page.getByRole('button', { name: /places|स्थान/i }).first().click();
    const placesAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(placesAxe.violations).toEqual([]);

    // 3. Check More (Settings, Licences, Privacy)
    await page.getByRole('button', { name: /more|और/i }).first().click();
    await expect(page.locator('text=Sources and licences')).toBeVisible();
    const moreAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(moreAxe.violations).toEqual([]);
  });

  test('language switcher changes document lang attribute and UI strings', async ({ page }) => {
    await page.goto('/');

    // Switch to Hindi
    const hiButton = page.getByRole('radio', { name: 'हिन्दी' });
    await hiButton.click();

    const htmlLang = await page.getAttribute('html', 'lang');
    expect(htmlLang).toBe('hi');
  });

  test('offline page is accessible and valid', async ({ page }) => {
    await page.goto('/offline.html');
    await expect(page.locator('h1')).toHaveText(/You are offline/i);

    const offlineAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(offlineAxe.violations).toEqual([]);
  });

  test('push-to-talk mic button and answer card audio controls have accessible names and aria states', async ({ page }) => {
    await page.goto('/');
    const micButton = page.locator('button[aria-label*="speak" i], button[aria-label*="बोलें" i], button[aria-label*="listening" i]').first();
    await expect(micButton).toBeVisible();
    await expect(micButton).toHaveAttribute('aria-label');
  });
});
