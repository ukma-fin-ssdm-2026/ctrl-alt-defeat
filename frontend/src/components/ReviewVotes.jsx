// "Support" / "Don't support" buttons of a review. The active choice is highlighted;
// the author sees the counters but cannot vote for their own review.
export default function ReviewVotes({ likes = 0, dislikes = 0, myVote = 0, isOwn = false, isLoggedIn = false, disabled = false, language = 'UKR', onVote }) {
  const isUkr = language === 'UKR';
  const ownHint = isUkr ? 'Не можна голосувати за власну рецензію' : 'You cannot vote for your own review';
  const loginHint = isUkr ? 'Увійдіть, щоб проголосувати' : 'Log in to vote';
  const hint = isOwn ? ownHint : (!isLoggedIn ? loginHint : undefined);

  const buttonClass = (active, activeClass, hoverClass) => [
    'flex items-center gap-1 px-2.5 py-1 rounded-full border font-semibold transition-colors',
    active ? activeClass : `border-gray-200 dark:border-gray-600 ${isOwn ? '' : hoverClass}`,
    isOwn || disabled ? 'cursor-default opacity-70' : '',
  ].join(' ');

  return (
    <div className="flex items-center gap-2" title={hint}>
      <button
        type="button"
        onClick={() => onVote(1)}
        disabled={isOwn || disabled}
        aria-pressed={myVote === 1}
        aria-label={`${isUkr ? 'Підтримую' : 'Support'} (${likes})`}
        className={buttonClass(myVote === 1, 'bg-green-500/15 border-green-500 text-green-700 dark:text-green-300', 'hover:border-green-500 hover:text-green-600')}
      >
        <span aria-hidden="true">👍</span> {isUkr ? 'Підтримую' : 'Support'} <span className="tabular-nums">{likes}</span>
      </button>
      <button
        type="button"
        onClick={() => onVote(-1)}
        disabled={isOwn || disabled}
        aria-pressed={myVote === -1}
        aria-label={`${isUkr ? 'Не підтримую' : "Don't support"} (${dislikes})`}
        className={buttonClass(myVote === -1, 'bg-red-500/15 border-red-500 text-red-700 dark:text-red-300', 'hover:border-red-500 hover:text-red-600')}
      >
        <span aria-hidden="true">👎</span> {isUkr ? 'Не підтримую' : "Don't support"} <span className="tabular-nums">{dislikes}</span>
      </button>
      {!isLoggedIn && !isOwn && <span className="text-[10px] text-gray-400">({isUkr ? 'потрібен вхід' : 'login required'})</span>}
    </div>
  );
}
