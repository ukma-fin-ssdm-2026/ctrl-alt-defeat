// Audience rating line for the movie page (US-008)

// Ukrainian plural: 1 оцінка, 2-4 оцінки, 5+ оцінок
function pluralizeRatings(count) {
  const lastTwo = count % 100;
  const last = count % 10;
  if (lastTwo >= 11 && lastTwo <= 14) return 'оцінок';
  if (last === 1) return 'оцінка';
  if (last >= 2 && last <= 4) return 'оцінки';
  return 'оцінок';
}

export function formatAudienceRating(summary, isUkr = true) {
  if (!summary) return '—';
  if (!summary.ratings_count) return isUkr ? 'Оцінок та рецензій ще немає' : 'No ratings or reviews yet';
  const count = summary.ratings_count;
  const label = isUkr ? pluralizeRatings(count) : (count === 1 ? 'rating' : 'ratings');
  return `★ ${summary.average_rating.toFixed(1)} / 10 · ${count} ${label}`;
}
