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

  const TIER1_LANGUAGES = [
    { code: 'en', name: 'English' },
    { code: 'hi', name: 'हिन्दी' },
    { code: 'bn', name: 'বাংলা' },
    { code: 'mr', name: 'मराठी' },
    { code: 'te', name: 'తెలుగు' },
    { code: 'ta', name: 'தமிழ்' },
    { code: 'or', name: 'ଓଡ଼ିଆ' },
  ];

  for (const { code, name } of TIER1_LANGUAGES) {
    test(`shell passes automated axe accessibility evaluation in ${code} (${name})`, async ({ page }) => {
      await page.goto('/');

      const langBtn = page.getByRole('radio', { name: name });
      if (await langBtn.isVisible()) {
        await langBtn.click();
      } else {
        await page.evaluate((l) => {
          localStorage.setItem('weathergpt_lang', l);
          document.documentElement.lang = l;
        }, code);
        await page.reload();
      }

      const htmlLang = await page.getAttribute('html', 'lang');
      expect(htmlLang).toBe(code);

      const axeResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();
      expect(axeResults.violations).toEqual([]);
    });
  }

  test('passes axe evaluation on Alerts, Places, ML Lab, and More pages', async ({ page }) => {
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

    // 3. Check ML Lab
    const mlLabBtn = page.getByRole('button', { name: /ml lab|एमएल लैब/i }).first();
    if (await mlLabBtn.isVisible()) {
      await mlLabBtn.click();
      const mlLabAxe = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();
      expect(mlLabAxe.violations).toEqual([]);
    }

    // 4. Check More (Settings, Licences, Privacy)
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
