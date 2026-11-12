// Theme and language chosen by the visitor, kept in this browser between visits.
// Storage can be unavailable (private mode, blocked site data): then the defaults are used.

export const THEME_KEY = 'pislya-tytriv:theme';
export const LANGUAGE_KEY = 'pislya-tytriv:language';

function read(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // The choice still works until the page is reloaded
  }
}

// Saved choice first, otherwise the system setting of the device
export function readDarkMode() {
  const saved = read(THEME_KEY);
  if (saved === 'dark') return true;
  if (saved === 'light') return false;
  try {
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
  } catch {
    return false;
  }
}

export function saveDarkMode(isDark) {
  write(THEME_KEY, isDark ? 'dark' : 'light');
}

export function readLanguage() {
  return read(LANGUAGE_KEY) === 'EN' ? 'EN' : 'UKR';
}

export function saveLanguage(language) {
  write(LANGUAGE_KEY, language);
}
