import { describe, expect, it } from 'vitest';
import { DETAILED_REVIEW_LENGTH } from './achievements';
import { RANKS, XP_RULES, activityXp, rankForXp, reachedRanks } from './ranks';

describe('user ranks', () => {
  it('gives XP for reviews, the watched list and the watchlist', () => {
    const reviews = [
      { review_text: 'Гарний фільм' },
      { review_text: null },
      { review_text: '   ' },
      { review_text: 'x'.repeat(DETAILED_REVIEW_LENGTH) },
    ];
    const xp = activityXp({ reviews, watched: [{}, {}], watchlist: [{}] });

    expect(xp).toBe(
      XP_RULES.textReview + 2 * XP_RULES.ratingOnly + XP_RULES.textReview + XP_RULES.detailedBonus
      + 2 * XP_RULES.watched + XP_RULES.watchlist,
    );
    expect(activityXp()).toBe(0);
  });

  it('starts every account as a viewer', () => {
    expect(rankForXp(0)).toMatchObject({ rank: { id: 'viewer' }, next: { id: 'fan' }, toNext: 25, progress: 0 });
  });

  it('switches the rank exactly at the threshold', () => {
    expect(rankForXp(74).rank.id).toBe('fan');
    expect(rankForXp(75)).toMatchObject({ rank: { id: 'reviewer' }, next: { id: 'critic' }, toNext: 75, progress: 0 });
    expect(rankForXp(100).progress).toBeCloseTo(25 / 75);
  });

  it('stops at the top rank', () => {
    expect(rankForXp(9999)).toMatchObject({ rank: { id: 'legend' }, next: null, toNext: 0, progress: 1 });
  });

  it('has ascending thresholds and its own colours for every rank', () => {
    RANKS.slice(1).forEach((rank, i) => expect(rank.minXp).toBeGreaterThan(RANKS[i].minXp));
    expect(new Set(RANKS.map(rank => rank.bar)).size).toBe(RANKS.length);
  });

  it('lists the reached ranks above the starting one', () => {
    expect(reachedRanks(10)).toEqual([]);
    expect(reachedRanks(160).map(rank => rank.id)).toEqual(['fan', 'reviewer', 'critic']);
  });
});
