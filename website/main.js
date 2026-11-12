(() => {
  const root = document.documentElement;
  const button = document.querySelector('.mode');
  if (!button) return;
  const key = root.dataset.themeKey;
  const preferred = matchMedia('(prefers-color-scheme: dark)');
  let mode = preferred.matches ? 'dark' : 'light';
  try { const saved = localStorage.getItem(key); if (saved === 'dark' || saved === 'light') mode = saved; } catch {}
  function apply() {
    root.dataset.theme = mode;
    button.textContent = mode === 'dark' ? 'Light' : 'Dark';
    button.setAttribute('aria-label', mode === 'dark' ? 'Use light mode' : 'Use dark mode');
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = getComputedStyle(root).getPropertyValue('--canvas').trim();
  }
  apply(); button.hidden = false;
  button.addEventListener('click', () => { mode = mode === 'dark' ? 'light' : 'dark'; apply(); try { localStorage.setItem(key, mode); } catch {} });
})();
