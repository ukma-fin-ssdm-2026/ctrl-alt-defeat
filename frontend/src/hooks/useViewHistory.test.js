import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import useViewHistory, { HOME_VIEW } from './useViewHistory';

const movie = { id: 1, content_id: '11111111-1111-4111-8111-111111111111', title: 'Дюна' };

// jsdom keeps history.state but does not fire popstate on back(): the browser does it, so the test does too
const pressBack = state => act(() => {
  window.history.replaceState(state, '');
  window.dispatchEvent(new PopStateEvent('popstate', { state }));
});

describe('pages in the browser history', () => {
  afterEach(() => window.history.replaceState(null, '', '/'));

  it('records each opened page and returns to the previous one with Back', () => {
    const { result } = renderHook(() => useViewHistory());
    expect(result.current.view).toEqual(HOME_VIEW);
    expect(window.history.state).toMatchObject({ view: HOME_VIEW, index: 0 });

    act(() => result.current.navigate({ category: 'Мультфільми' }));
    const cartoons = window.history.state;
    act(() => result.current.navigate({ category: 'Мультфільми', movie }));
    expect(result.current.view).toMatchObject({ category: 'Мультфільми', movie });
    expect(window.history.state.index).toBe(2);

    pressBack(cartoons);
    expect(result.current.view).toEqual({ ...HOME_VIEW, category: 'Мультфільми' });
  });

  it('does not add a history entry for the page already shown', () => {
    const { result } = renderHook(() => useViewHistory());
    const before = window.history.length;
    act(() => result.current.navigate({ profile: true }));
    act(() => result.current.navigate({ profile: true }));
    expect(window.history.length).toBe(before + 1);
  });

  it('keeps the page after a reload and goes home when there is no earlier page', () => {
    window.history.replaceState({ view: { movie }, index: 0 }, '');
    const { result } = renderHook(() => useViewHistory());
    // Restored from the history entry of the reloaded page
    expect(result.current.view.movie).toEqual(movie);

    act(() => result.current.goBack());
    expect(result.current.view).toEqual(HOME_VIEW);
  });
});
