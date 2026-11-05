// User rank from experience points (XP) earned by real activity on the site.
// Tailwind classes are full static strings so the JIT compiler keeps them in the build.
import { DETAILED_REVIEW_LENGTH } from './achievements';

export const XP_RULES = {
  textReview: 10,
  ratingOnly: 5,
  detailedBonus: 5,
  watched: 3,
  watchlist: 1,
};

export const RANKS = [
  {
    id: 'viewer', icon: '🎟️', minXp: 0,
    titleUkr: 'Глядач', titleEn: 'Viewer',
    chip: 'bg-slate-500/10 text-slate-600 dark:text-slate-300 ring-slate-400/40',
    bar: 'bg-slate-400',
  },
  {
    id: 'fan', icon: '🍿', minXp: 25,
    titleUkr: 'Кінолюб', titleEn: 'Movie Fan',
    chip: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 ring-emerald-400/50',
    bar: 'bg-emerald-500',
  },
  {
    id: 'reviewer', icon: '✍️', minXp: 75,
    titleUkr: 'Рецензент', titleEn: 'Reviewer',
    chip: 'bg-sky-500/10 text-sky-700 dark:text-sky-300 ring-sky-400/50',
    bar: 'bg-sky-500',
  },
  {
    id: 'critic', icon: '🎬', minXp: 150,
    titleUkr: 'Кінокритик', titleEn: 'Film Critic',
    chip: 'bg-violet-500/10 text-violet-700 dark:text-violet-300 ring-violet-400/50',
    bar: 'bg-violet-500',
  },
  {
    id: 'expert', icon: '🏆', minXp: 300,
    titleUkr: 'Кіноексперт', titleEn: 'Movie Expert',
    chip: 'bg-amber-500/15 text-amber-700 dark:text-amber-300 ring-amber-400/60',
    bar: 'bg-amber-500',
  },
  {
    id: 'legend', icon: '👑', minXp: 500,
    titleUkr: 'Легенда «Після титрів»', titleEn: 'After Credits Legend',
    chip: 'bg-gradient-to-r from-rose-500/15 via-fuchsia-500/15 to-amber-500/15 text-rose-700 dark:text-rose-300 ring-rose-400/60',
    bar: 'bg-gradient-to-r from-rose-500 via-fuchsia-500 to-amber-500',
  },
];

export function activityXp({ reviews = [], watched = [], watchlist = [] } = {}) {
  const reviewXp = reviews.reduce((sum, review) => {
    const text = (review.review_text || '').trim();
    if (!text) return sum + XP_RULES.ratingOnly;
    return sum + XP_RULES.textReview + (text.length >= DETAILED_REVIEW_LENGTH ? XP_RULES.detailedBonus : 0);
  }, 0);
  return reviewXp + watched.length * XP_RULES.watched + watchlist.length * XP_RULES.watchlist;
}

// Current rank, the next one and how far the user is from it (progress 0..1; 1 at the top rank)
export function rankForXp(xp) {
  const index = RANKS.reduce((found, rank, i) => (xp >= rank.minXp ? i : found), 0);
  const rank = RANKS[index];
  const next = RANKS[index + 1] || null;
  if (!next) return { xp, rank, next: null, toNext: 0, progress: 1 };
  return {
    xp,
    rank,
    next,
    toNext: next.minXp - xp,
    progress: (xp - rank.minXp) / (next.minXp - rank.minXp),
  };
}

// Ranks the user has reached above the starting one (used for "new rank" pop-ups)
export function reachedRanks(xp) {
  return RANKS.filter((rank, i) => i > 0 && xp >= rank.minXp);
}
