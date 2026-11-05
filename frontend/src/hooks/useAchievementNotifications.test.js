import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import useAchievementNotifications from './useAchievementNotifications';

const user = { user_id: 'u-1', created_at: '2026-11-05T10:00:00Z' };
const NOW = new Date('2026-11-05T12:00:00Z').getTime();
const review = { review_text: 'Гарний фільм' };
const base = { user, reviews: [], watched: [], watchlist: [], ready: true, now: NOW };

describe('achievement notifications', () => {
  beforeEach(() => window.localStorage.clear());

  it('does not announce badges the account already had in this browser', () => {
    const { result } = renderHook(() => useAchievementNotifications({ ...base, reviews: [review] }));

    expect(result.current.current).toBeNull();
    expect(JSON.parse(window.localStorage.getItem('achievements-seen:u-1'))).toEqual(['first-review']);
  });

  it('announces a newly unlocked badge once', () => {
    const { result, rerender } = renderHook(props => useAchievementNotifications(props), { initialProps: base });
    expect(result.current.current).toBeNull();

    rerender({ ...base, reviews: [review] });
    expect(result.current.current).toMatchObject({ id: 'first-review', unlocked: true });

    act(() => result.current.dismiss());
    expect(result.current.current).toBeNull();

    // Losing the badge and earning it again does not repeat the pop-up
    rerender(base);
    rerender({ ...base, reviews: [review] });
    expect(result.current.current).toBeNull();
  });

  it('queues several new badges and waits until the data is loaded', () => {
    const { result, rerender } = renderHook(props => useAchievementNotifications(props), { initialProps: base });
    const five = Array.from({ length: 5 }, (_, id) => ({ id, genres: ['Драма'] }));

    rerender({ ...base, reviews: [review], watchlist: five, ready: false });
    expect(result.current.current).toBeNull();

    rerender({ ...base, reviews: [review], watchlist: five });
    expect(result.current.current.id).toBe('first-review');
    expect(result.current.pending).toBe(1);

    act(() => result.current.dismiss());
    expect(result.current.current.id).toBe('planner');
    expect(result.current.pending).toBe(0);
  });

  it('stays silent for guests', () => {
    const { result } = renderHook(() => useAchievementNotifications({ ...base, user: null, reviews: [review] }));

    expect(result.current.current).toBeNull();
    expect(window.localStorage.length).toBe(0);
  });
});

describe('rank notifications', () => {
  beforeEach(() => window.localStorage.clear());

  it('announces a new rank like a badge', () => {
    const { result, rerender } = renderHook(props => useAchievementNotifications(props), { initialProps: base });
    const watched = Array.from({ length: 9 }, (_, id) => ({ id, genres: ['Драма'] }));

    // 9 watched * 3 XP = 27 XP → "Кінолюб"
    rerender({ ...base, watched });
    expect(result.current.current).toMatchObject({ kind: 'rank', id: 'rank-fan', titleUkr: 'Кінолюб' });
  });
});
