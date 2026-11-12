// Applies the remembered dark theme before React starts (same key as src/utils/preferences.js)
try {
  var theme = localStorage.getItem('pislya-tytriv:theme');
  if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
  }
} catch {
  // Storage blocked: the app applies the theme itself after loading
}
