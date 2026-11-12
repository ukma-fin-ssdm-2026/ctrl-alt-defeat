import { useCallback, useEffect, useRef, useState } from 'react';

// The site has one address: which page is shown (home with filters, a movie, the profile, the admin page)
// is kept in the browser history, so the Back button returns to the previous page instead of leaving
// the site, and a reload keeps the current page.
export const HOME_VIEW = { movie: null, profile: false, admin: false, category: null, genre: null, year: null };

const toView = value => ({ ...HOME_VIEW, ...(value || {}) });

function currentEntry() {
  const state = window.history.state;
  return state && state.view ? { view: toView(state.view), index: state.index || 0 } : null;
}

export default function useViewHistory() {
  const [entry, setEntry] = useState(() => currentEntry() || { view: HOME_VIEW, index: 0 });
  // The entry shown right now, for navigate() called several times before a re-render
  const shown = useRef(entry);

  const show = useCallback(next => {
    shown.current = next;
    setEntry(next);
  }, []);

  // The first page of this visit (or the page restored after a reload) is the current history entry
  useEffect(() => {
    const first = shown.current;
    window.history.replaceState({ ...(window.history.state || {}), view: first.view, index: first.index }, '');
    const onPopState = () => show(currentEntry() || { view: HOME_VIEW, index: 0 });
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [show]);

  // Open a page: a new history entry, unless it is the page already shown
  const navigate = useCallback(patch => {
    const view = toView(patch);
    if (JSON.stringify(view) === JSON.stringify(shown.current.view)) return;
    const next = { view, index: shown.current.index + 1 };
    window.history.pushState({ view, index: next.index }, '');
    show(next);
  }, [show]);

  // "Back" inside the site: the previous page, or home if this page was opened first
  const goBack = useCallback(() => {
    if (shown.current.index > 0) {
      window.history.back();
    } else {
      navigate(HOME_VIEW);
    }
  }, [navigate]);

  return { view: entry.view, navigate, goBack };
}
