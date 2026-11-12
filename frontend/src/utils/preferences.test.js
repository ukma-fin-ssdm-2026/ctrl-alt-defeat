import { afterEach, describe, expect, it, vi } from 'vitest';
import { LANGUAGE_KEY, THEME_KEY, readDarkMode, readLanguage, saveDarkMode, saveLanguage } from './preferences';

describe('remembered theme and language', () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('keeps the chosen theme and language between visits', () => {
    saveDarkMode(true);
    saveLanguage('EN');
    expect(window.localStorage.getItem(THEME_KEY)).toBe('dark');
    expect(readDarkMode()).toBe(true);
    expect(readLanguage()).toBe('EN');

    saveDarkMode(false);
    saveLanguage('UKR');
    expect(readDarkMode()).toBe(false);
    expect(window.localStorage.getItem(LANGUAGE_KEY)).toBe('UKR');
    expect(readLanguage()).toBe('UKR');
  });

  it('follows the system theme until the visitor chooses one', () => {
    vi.stubGlobal('matchMedia', query => ({ matches: query === '(prefers-color-scheme: dark)' }));
    expect(readDarkMode()).toBe(true);
    vi.stubGlobal('matchMedia', () => ({ matches: false }));
    expect(readDarkMode()).toBe(false);
    expect(readLanguage()).toBe('UKR');
  });

  it('works without storage (private mode, blocked site data)', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    vi.stubGlobal('matchMedia', undefined);

    expect(() => saveDarkMode(true)).not.toThrow();
    expect(readDarkMode()).toBe(false);
    expect(readLanguage()).toBe('UKR');
  });
});
