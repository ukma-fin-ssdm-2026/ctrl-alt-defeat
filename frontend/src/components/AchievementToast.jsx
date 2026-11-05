import { useEffect } from 'react';

export const ACHIEVEMENT_TOAST_MS = 9000;

// Pop-up shown when the user unlocks a new achievement, with a shortcut to the badge in the profile
export default function AchievementToast({ badge, pending = 0, language = 'UKR', onView, onClose }) {
  const isUkr = language === 'UKR';

  useEffect(() => {
    if (!badge) return undefined;
    const timer = setTimeout(onClose, ACHIEVEMENT_TOAST_MS);
    return () => clearTimeout(timer);
  }, [badge, onClose]);

  if (!badge) return null;

  return (
    <div
      key={badge.id}
      role="status"
      aria-live="polite"
      className="achievement-toast fixed bottom-4 left-4 right-4 sm:right-auto z-50 sm:w-96 overflow-hidden rounded-2xl border border-yellow-400/60 bg-white dark:bg-gray-800 shadow-2xl"
    >
      <div className="h-1 bg-gradient-to-r from-yellow-300 via-yellow-500 to-orange-500"></div>
      <div className="p-4 flex items-start gap-4">
        <div className="achievement-toast-icon shrink-0 w-14 h-14 rounded-full bg-yellow-100 dark:bg-yellow-500/20 ring-2 ring-yellow-400 flex items-center justify-center text-3xl" aria-hidden="true">
          {badge.icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-black uppercase tracking-wider text-yellow-600 dark:text-yellow-400">
            {isUkr ? '🏆 Нова нагорода!' : '🏆 New achievement!'}
          </p>
          <p className="font-black text-gray-900 dark:text-white leading-tight mt-0.5">
            {isUkr ? badge.titleUkr : badge.titleEn}
          </p>
          <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
            {isUkr ? badge.descUkr : badge.descEn}
          </p>
          <div className="flex items-center gap-3 mt-3">
            <button
              type="button"
              onClick={() => onView(badge)}
              className="px-3 py-1.5 rounded-lg bg-yellow-500 hover:bg-yellow-400 text-gray-900 text-xs font-bold transition-colors"
            >
              {isUkr ? 'Переглянути' : 'View'}
            </button>
            {pending > 0 && (
              <span className="text-[11px] text-gray-500 dark:text-gray-400">
                {isUkr ? `і ще ${pending}` : `and ${pending} more`}
              </span>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label={isUkr ? 'Закрити' : 'Close'}
          className="shrink-0 text-gray-400 hover:text-gray-700 dark:hover:text-white font-bold"
        >
          ✕
        </button>
      </div>
      <div className="achievement-toast-timer h-0.5 bg-yellow-500/70" style={{ animationDuration: `${ACHIEVEMENT_TOAST_MS}ms` }}></div>
    </div>
  );
}
