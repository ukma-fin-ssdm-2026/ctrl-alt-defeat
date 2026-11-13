// Profile achievements computed from the user's real activity:
// reviews from the API, the watchlist (FR-005), the watched list (FR-006)
// and the registration date (users.created_at).

const DAY_MS = 24 * 60 * 60 * 1000;
export const DETAILED_REVIEW_LENGTH = 300;

const reviewCount = ({ reviews }) => reviews.length;
const detailedReviewCount = ({ reviews }) =>
  reviews.filter(review => (review.review_text || '').trim().length >= DETAILED_REVIEW_LENGTH).length;
const watchedCount = ({ watched }) => watched.length;
const watchlistCount = ({ watchlist }) => watchlist.length;
const watchedGenreCount = ({ watched }) => {
  const genres = new Set();
  watched.forEach(movie => {
    const list = movie.genres?.length ? movie.genres : [movie.genre];
    list.filter(Boolean).forEach(genre => genres.add(genre));
  });
  return genres.size;
};
const daysSinceRegistration = ({ createdAt, now }) => {
  const registered = createdAt ? new Date(createdAt).getTime() : Number.NaN;
  if (Number.isNaN(registered)) return 0;
  return Math.max(0, Math.floor((now - registered) / DAY_MS));
};

export const ACHIEVEMENTS = [
  {
    id: 'first-review', icon: '🖊️', target: 1, value: reviewCount,
    titleUkr: 'Перше слово', titleEn: 'First Word',
    descUkr: 'Напишіть свою першу рецензію', descEn: 'Write your first review',
  },
  {
    id: 'reviewer', icon: '🥇', target: 10, value: reviewCount,
    titleUkr: 'Легендарний рецензент', titleEn: 'Legendary Reviewer',
    descUkr: 'Напишіть 10 рецензій', descEn: 'Write 10 reviews',
  },
  {
    id: 'detailed', icon: '📝', target: 1, value: detailedReviewCount,
    titleUkr: 'Розгорнута думка', titleEn: 'In-Depth Take',
    descUkr: `Напишіть рецензію довжиною від ${DETAILED_REVIEW_LENGTH} символів`,
    descEn: `Write a review of at least ${DETAILED_REVIEW_LENGTH} characters`,
  },
  {
    id: 'planner', icon: '📋', target: 5, value: watchlistCount,
    titleUkr: 'Є плани на вечір', titleEn: 'Evening Planner',
    descUkr: 'Додайте 5 фільмів до списку «До перегляду»', descEn: 'Add 5 titles to your watchlist',
  },
  {
    id: 'cinephile', icon: '🎬', target: 10, value: watchedCount,
    titleUkr: 'Кіноман', titleEn: 'Cinephile',
    descUkr: 'Позначте 10 фільмів як переглянуті', descEn: 'Mark 10 titles as watched',
  },
  {
    id: 'omnivore', icon: '🎭', target: 5, value: watchedGenreCount,
    titleUkr: 'Всеїдний глядач', titleEn: 'Genre Explorer',
    descUkr: 'Перегляньте фільми 5 різних жанрів', descEn: 'Watch titles from 5 different genres',
  },
  {
    id: 'veteran', icon: '🛡️', target: 30, value: daysSinceRegistration,
    titleUkr: 'Ветеран платформи', titleEn: 'Platform Veteran',
    descUkr: 'Будьте з нами 30 днів від реєстрації', descEn: 'Stay with us for 30 days after registration',
  },
];

export function computeAchievements({ reviews = [], watched = [], watchlist = [], createdAt = null, now = Date.now() } = {}) {
  const data = { reviews, watched, watchlist, createdAt, now };
  return ACHIEVEMENTS.map(({ value, ...badge }) => {
    const current = value(data);
    return {
      ...badge,
      progress: Math.min(current, badge.target),
      unlocked: current >= badge.target,
    };
  });
}
