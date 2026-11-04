import { describe, expect, it } from 'vitest';
import { formatAudienceRating } from './audienceRating';

const summary = (average_rating, ratings_count) => ({ average_rating, ratings_count, reviews_count: 0, distribution: {} });

describe('formatAudienceRating (US-008)', () => {
  it('shows the average and the number of ratings', () => {
    // Trace: T-023
    expect(formatAudienceRating(summary(8.6667, 3))).toBe('★ 8.7 / 10 · 3 оцінки');
  });

  it.each([
    [1, 'оцінка'], [2, 'оцінки'], [4, 'оцінки'], [5, 'оцінок'], [11, 'оцінок'], [14, 'оцінок'], [21, 'оцінка'], [22, 'оцінки'], [25, 'оцінок'], [111, 'оцінок'],
  ])('uses the right Ukrainian plural for %i', (count, word) => {
    // Trace: T-023
    expect(formatAudienceRating(summary(9, count))).toBe(`★ 9.0 / 10 · ${count} ${word}`);
  });

  it('says there are no ratings yet for a movie without reviews', () => {
    // Trace: T-024
    expect(formatAudienceRating(summary(null, 0))).toBe('Оцінок та рецензій ще немає');
    expect(formatAudienceRating(summary(null, 0), false)).toBe('No ratings or reviews yet');
  });

  it('uses English wording in the English interface', () => {
    // Trace: T-023
    expect(formatAudienceRating(summary(7, 1), false)).toBe('★ 7.0 / 10 · 1 rating');
    expect(formatAudienceRating(summary(7, 2), false)).toBe('★ 7.0 / 10 · 2 ratings');
  });

  it('shows a dash while the summary is not loaded', () => {
    // Trace: T-023
    expect(formatAudienceRating(null)).toBe('—');
  });
});
