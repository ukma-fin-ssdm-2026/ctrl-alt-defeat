import { describeBan } from '../utils/ban';

// FR-009: shown instead of the review and comment forms to a banned user
export default function BanNotice({ ban, language = 'UKR', compact = false }) {
  const isUkr = language === 'UKR';
  if (!ban) return null;
  return (
    <div
      role="status"
      className={`bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700/50 text-red-700 dark:text-red-200 rounded-xl ${compact ? 'p-2 text-xs mt-2' : 'p-4 text-sm'}`}
    >
      <p className="font-semibold">{describeBan(ban, language)}</p>
      {!compact && (
        <p className="mt-1 text-xs opacity-80">
          {isUkr
            ? 'Поки діє блокування, не можна писати рецензії, ставити оцінки й коментувати. Watchlist, переглянуте та рекомендації доступні.'
            : 'While the ban is in force you cannot review, rate or comment. Watchlist, watched list and recommendations stay available.'}
        </p>
      )}
    </div>
  );
}
