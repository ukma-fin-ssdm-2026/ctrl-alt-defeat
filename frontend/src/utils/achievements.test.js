import { describe, expect, it } from 'vitest';
import { ACHIEVEMENTS, DETAILED_REVIEW_LENGTH, computeAchievements } from './achievements';

const byId = (list) => Object.fromEntries(list.map(badge => [badge.id, badge]));
const review = (text = 'Гарний фільм, раджу') => ({ review_text: text });
const movie = (...genres) => ({ genres });
const NOW = new Date('2026-11-05T12:00:00Z').getTime();

describe('profile achievements', () => {
  it('locks every badge for a brand-new account', () => {
    const badges = computeAchievements({ createdAt: '2026-11-05T10:00:00Z', now: NOW });

    expect(badges).toHaveLength(ACHIEVEMENTS.length);
    expect(badges.every(badge => !badge.unlocked && badge.progress === 0)).toBe(true);
  });

  it('counts reviews and caps progress at the target', () => {
    const one = byId(computeAchievements({ reviews: [review()], now: NOW }));
    expect(one['first-review']).toMatchObject({ unlocked: true, progress: 1 });
    expect(one.reviewer).toMatchObject({ unlocked: false, progress: 1, target: 10 });

    const many = byId(computeAchievements({ reviews: Array.from({ length: 12 }, () => review()), now: NOW }));
    expect(many.reviewer).toMatchObject({ unlocked: true, progress: 10 });
  });

  it('needs a long text for the detailed review badge', () => {
    const short = byId(computeAchievements({ reviews: [review('x'.repeat(DETAILED_REVIEW_LENGTH - 1)), { review_text: null }], now: NOW }));
    expect(short.detailed.unlocked).toBe(false);

    const long = byId(computeAchievements({ reviews: [review(`  ${'x'.repeat(DETAILED_REVIEW_LENGTH)}  `)], now: NOW }));
    expect(long.detailed.unlocked).toBe(true);
  });

  it('uses the watchlist and the watched list', () => {
    const badges = byId(computeAchievements({
      watchlist: Array.from({ length: 5 }, () => movie('Драма')),
      watched: Array.from({ length: 9 }, () => movie('Драма')),
      now: NOW,
    }));

    expect(badges.planner.unlocked).toBe(true);
    expect(badges.cinephile).toMatchObject({ unlocked: false, progress: 9 });
  });

  it('counts distinct genres of watched titles', () => {
    const watched = [movie('Драма', 'Трилер'), movie('Драма', 'Комедія'), { genre: 'Жахи' }, movie()];
    const four = byId(computeAchievements({ watched, now: NOW }));
    expect(four.omnivore).toMatchObject({ unlocked: false, progress: 4 });

    const five = byId(computeAchievements({ watched: [...watched, movie('Фантастика')], now: NOW }));
    expect(five.omnivore.unlocked).toBe(true);
  });

  it('counts full days since registration', () => {
    const fresh = byId(computeAchievements({ createdAt: '2026-10-06T13:00:00Z', now: NOW }));
    expect(fresh.veteran).toMatchObject({ unlocked: false, progress: 29 });

    const old = byId(computeAchievements({ createdAt: '2026-10-06T12:00:00Z', now: NOW }));
    expect(old.veteran.unlocked).toBe(true);

    expect(byId(computeAchievements({ createdAt: 'not-a-date', now: NOW })).veteran.progress).toBe(0);
  });
});
