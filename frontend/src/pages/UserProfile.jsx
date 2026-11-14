import { useEffect, useState } from 'react';
import apiClient from '../api/client';
import { forgetStoredToken } from '../auth/currentUser';
import { getDisplayName } from '../utils/displayName';
import { computeAchievements } from '../utils/achievements';
import { RANKS, XP_RULES, activityXp, rankForXp } from '../utils/ranks';
import { posterFor } from '../utils/poster';
import { translateGenre } from '../utils/genres';

// content_id of a catalog title
const CONTENT_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function UserProfile({ 
  user, 
  language, 
  watchlistMovies, 
  watchedMovies = [],
  onSelectMovie, 
  onToggleWatchlist, 
  onToggleWatched,
  onDeleteProfile,
  initialTab = 'general',
  highlightAchievement = null,
}) {
  const [activeTab, setActiveTab] = useState(initialTab); // 'general', 'security', 'watchlist', 'watched', 'reviews', 'achievements'
  
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordMessage, setPasswordMessage] = useState({ ok: false, text: '' });
  const [savingPassword, setSavingPassword] = useState(false);
  // Account deletion is confirmed with the current password
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const canDeleteAccount = user?.role !== 'admin';

  const isUkr = language === 'UKR';
  // Title and genre of a title in the interface language (lists of the profile)
  const titleOf = movie => (isUkr ? movie.title : (movie.title_en || movie.titleEn || movie.title)) || (isUkr ? 'Фільм' : 'Title');
  const genreOf = movie => translateGenre(movie.genre, isUkr ? 'UKR' : 'EN');
  // Real date from the server (users.created_at), e.g. "5 листопада 2026 р."
  const registrationDate = user?.created_at
    ? new Date(user.created_at).toLocaleDateString(isUkr ? 'uk-UA' : 'en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
    : '—';

  // Real reviews of the current user from the API (previously hardcoded examples)
  const userId = user?.user_id;
  const [reviewsState, setReviewsState] = useState({ userId: null, items: [], error: false });
  useEffect(() => {
    if (!userId) return undefined;
    let ignore = false;
    apiClient.get('/reviews', { params: { user_id: userId, limit: 100 } })
      .then(response => { if (!ignore) setReviewsState({ userId, items: response.data.items || [], error: false }); })
      .catch(() => { if (!ignore) setReviewsState({ userId, items: [], error: true }); });
    return () => { ignore = true; };
  }, [userId]);
  const reviewsLoaded = reviewsState.userId === userId;

  // A review opens the page of its title: the full card comes from the catalog API; if that fails,
  // the page opens with what the review knows and loads the rest itself
  const openReviewedTitle = review => {
    if (!onSelectMovie) return;
    const fallback = {
      content_id: review.content_id,
      title: review.content_title,
      title_en: review.content_title_en,
      img: review.content_img,
      img_en: review.content_img_en,
    };
    // Only a real UUID goes into the request path (and encoded): a broken value cannot reach another endpoint
    const contentId = String(review.content_id ?? '');
    if (!CONTENT_UUID.test(contentId)) {
      onSelectMovie(fallback);
      return;
    }
    Promise.resolve(apiClient.get(`/movies/${encodeURIComponent(contentId)}`))
      .then(response => onSelectMovie(response?.data?.content_id ? response.data : fallback))
      .catch(() => onSelectMovie(fallback));
  };
  const userReviews = reviewsLoaded ? reviewsState.items : [];

  // Badges computed from real activity instead of hardcoded "unlocked" examples
  const achievements = computeAchievements({
    reviews: userReviews,
    watched: watchedMovies,
    watchlist: watchlistMovies || [],
    createdAt: user?.created_at,
  });
  const unlockedCount = achievements.filter(badge => badge.unlocked).length;
  // Rank from XP for real activity (reviews, watched list, watchlist)
  const rankInfo = rankForXp(activityXp({ reviews: userReviews, watched: watchedMovies, watchlist: watchlistMovies || [] }));
  const rankTitle = rank => (isUkr ? rank.titleUkr : rank.titleEn);

  const accountErrorText = (code) => {
    if (code === 'INVALID_PASSWORD') return isUkr ? 'Поточний пароль неправильний.' : 'The current password is incorrect.';
    if (code === 'SAME_PASSWORD') return isUkr ? 'Новий пароль має відрізнятися від поточного.' : 'The new password must differ from the current one.';
    if (code === 'SEED_ACCOUNT_LOCKED') return isUkr ? 'Демо-акаунт не можна змінити чи видалити: ним користуються всі відвідувачі.' : 'The demo account cannot be changed or deleted: all visitors use it.';
    if (code === 'ADMIN_ACCOUNT') return isUkr ? 'Акаунт адміністратора не можна видалити з профілю.' : 'An administrator account cannot be deleted from the profile.';
    if (code === 'VALIDATION_ERROR') return isUkr ? 'Новий пароль — щонайменше 6 символів.' : 'The new password needs at least 6 characters.';
    return isUkr ? 'Не вдалося виконати дію. Спробуйте ще раз.' : 'Something went wrong. Please try again.';
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordMessage({ ok: false, text: isUkr ? 'Заповніть усі поля!' : 'Fill in all fields!' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordMessage({ ok: false, text: isUkr ? 'Нові паролі не збігаються!' : 'New passwords do not match!' });
      return;
    }
    setSavingPassword(true);
    try {
      await apiClient.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword });
      // Other sessions end; this one continues with the new cookie set by the server
      forgetStoredToken();
      setPasswordMessage({ ok: true, text: isUkr ? 'Пароль успішно змінено!' : 'Password successfully changed!' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPasswordMessage({ ok: false, text: accountErrorText(err.response?.data?.error?.code) });
    } finally {
      setSavingPassword(false);
    }
  };

  const handleDeleteAccount = async (e) => {
    e.preventDefault();
    if (!deletePassword) {
      setDeleteError(isUkr ? 'Введіть пароль для підтвердження.' : 'Enter your password to confirm.');
      return;
    }
    setDeleting(true);
    setDeleteError('');
    try {
      await apiClient.delete('/auth/me', { data: { password: deletePassword } });
      onDeleteProfile?.();
    } catch (err) {
      setDeleteError(accountErrorText(err.response?.data?.error?.code));
      setDeleting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      
      {/* Шапка профілю */}
      <div className="bg-white dark:bg-gray-800 rounded-3xl p-6 shadow-xl border border-gray-100 dark:border-gray-700 flex flex-col sm:flex-row items-center gap-6 mb-8">
        <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-yellow-500 to-amber-300 flex items-center justify-center text-4xl font-black text-gray-900 shadow-inner">
          {getDisplayName(user)[0]?.toUpperCase() || 'U'}
        </div>
        <div className="text-center sm:text-left flex-1">
          <h1 className="text-2xl font-black text-gray-900 dark:text-white">
            {getDisplayName(user) || (isUkr ? 'Користувач' : 'User')}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {user?.email || 'user@gmail.com'}
          </p>
          <button
            type="button"
            onClick={() => setActiveTab('achievements')}
            data-testid="rank-chip"
            data-rank={rankInfo.rank.id}
            title={isUkr ? 'Як підвищити ранг' : 'How to rank up'}
            className={`inline-flex items-center gap-2 mt-3 px-3 py-1 rounded-full text-xs font-bold ring-1 transition-transform hover:scale-105 ${rankInfo.rank.chip}`}
          >
            <span aria-hidden="true">{rankInfo.rank.icon}</span>
            {isUkr ? 'Ранг' : 'Rank'}: {rankTitle(rankInfo.rank)}
            <span className="opacity-70 font-semibold">· {rankInfo.xp} XP</span>
          </button>
          <div className="mt-2 max-w-xs mx-auto sm:mx-0">
            <div className="h-1.5 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${rankInfo.rank.bar}`} style={{ width: `${Math.round(rankInfo.progress * 100)}%` }}></div>
            </div>
            <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
              {rankInfo.next
                ? (isUkr
                  ? `До рангу «${rankTitle(rankInfo.next)}» ще ${rankInfo.toNext} XP`
                  : `${rankInfo.toNext} XP to "${rankTitle(rankInfo.next)}"`)
                : (isUkr ? 'Найвищий ранг досягнуто!' : 'Top rank reached!')}
            </p>
          </div>
        </div>
      </div>

      {/* Меню у стилі Telegram та контент */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* Бічна панель навігації */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-3 shadow-md border border-gray-100 dark:border-gray-700 space-y-1 h-fit">
          
          <button 
            onClick={() => setActiveTab('general')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition-all ${activeTab === 'general' ? 'bg-yellow-500 text-gray-900 shadow-md' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'}`}
          >
            <span>⚙️</span> {isUkr ? 'Загальне' : 'General'}
          </button>

          <button 
            onClick={() => setActiveTab('security')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition-all ${activeTab === 'security' ? 'bg-yellow-500 text-gray-900 shadow-md' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'}`}
          >
            <span>🔒</span> {isUkr ? 'Безпека' : 'Security'}
          </button>

          <button 
            onClick={() => setActiveTab('watchlist')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition-all ${activeTab === 'watchlist' ? 'bg-yellow-500 text-gray-900 shadow-md' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'}`}
          >
            <span>⭐</span> {isUkr ? 'Обране' : 'Watchlist'} <span className="ml-auto text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded-full">{watchlistMovies.length}</span>
          </button>

          <button 
            onClick={() => setActiveTab('watched')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition-all ${activeTab === 'watched' ? 'bg-yellow-500 text-gray-900 shadow-md' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'}`}
          >
            <span>👁️</span> {isUkr ? 'Переглянуто' : 'Watched'} <span className="ml-auto text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded-full">{watchedMovies.length}</span>
          </button>

          <button 
            onClick={() => setActiveTab('reviews')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition-all ${activeTab === 'reviews' ? 'bg-yellow-500 text-gray-900 shadow-md' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'}`}
          >
            <span>💬</span> {isUkr ? 'Мої відгуки' : 'My Reviews'} <span className="ml-auto text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded-full">{userReviews.length}</span>
          </button>

          <button 
            onClick={() => setActiveTab('achievements')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition-all ${activeTab === 'achievements' ? 'bg-yellow-500 text-gray-900 shadow-md' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'}`}
          >
            <span>🏆</span> {isUkr ? 'Нагороди' : 'Achievements'} <span className="ml-auto text-xs px-2 py-0.5 bg-yellow-400 text-gray-900 rounded-full font-black">{unlockedCount}/{achievements.length}</span>
          </button>

          {canDeleteAccount && (
            <div className="pt-3 mt-3 border-t border-gray-100 dark:border-gray-700">
              <button 
                onClick={() => { setActiveTab('delete'); setDeleteError(''); }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm text-red-600 transition-all ${activeTab === 'delete' ? 'bg-red-50 dark:bg-red-900/20' : 'hover:bg-red-50 dark:hover:bg-red-900/20'}`}
              >
                <span>🗑️</span> {isUkr ? 'Видалити акаунт' : 'Delete Account'}
              </button>
            </div>
          )}

        </div>

        {/* Контент активної вкладки */}
        <div className="md:col-span-3 bg-white dark:bg-gray-800 rounded-3xl p-6 shadow-xl border border-gray-100 dark:border-gray-700">
          
          {/* 1. GENERAL */}
          {activeTab === 'general' && (
            <div className="space-y-6">
              <h2 className="text-xl font-black text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-4">
                {isUkr ? 'Загальна інформація про акаунт' : 'General Information'}
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-2xl">
                  <span className="text-xs text-gray-400 font-bold uppercase">{isUkr ? "Ім'я користувача" : 'Username'}</span>
                  <p className="text-base font-bold text-gray-800 dark:text-gray-100 mt-1">{getDisplayName(user)}</p>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-2xl">
                  <span className="text-xs text-gray-400 font-bold uppercase">Email</span>
                  <p className="text-base font-bold text-gray-800 dark:text-gray-100 mt-1">{user?.email}</p>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-2xl">
                  <span className="text-xs text-gray-400 font-bold uppercase">{isUkr ? 'Дата реєстрації' : 'Registration Date'}</span>
                  <p className="text-base font-bold text-gray-800 dark:text-gray-100 mt-1">{registrationDate}</p>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-2xl">
                  <span className="text-xs text-gray-400 font-bold uppercase">{isUkr ? 'Обраних фільмів' : 'Watchlist Items'}</span>
                  <p className="text-base font-bold text-gray-800 dark:text-gray-100 mt-1">{watchlistMovies.length}</p>
                </div>
              </div>
            </div>
          )}

          {/* 2. SECURITY */}
          {activeTab === 'security' && (
            <div className="space-y-6">
              <h2 className="text-xl font-black text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-4">
                {isUkr ? 'Безпека та зміна пароля' : 'Security & Password'}
              </h2>

              <form onSubmit={handlePasswordChange} className="space-y-4 max-w-md">
                <div>
                  <label htmlFor="current-password" className="block text-xs font-bold text-gray-500 uppercase mb-1">
                    {isUkr ? 'Поточний пароль' : 'Current Password'}
                  </label>
                  <input 
                    id="current-password"
                    type="password"
                    autoComplete="current-password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label htmlFor="new-password" className="block text-xs font-bold text-gray-500 uppercase mb-1">
                    {isUkr ? 'Новий пароль' : 'New Password'}
                  </label>
                  <input 
                    id="new-password"
                    type="password"
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label htmlFor="confirm-password" className="block text-xs font-bold text-gray-500 uppercase mb-1">
                    {isUkr ? 'Підтвердіть новий пароль' : 'Confirm New Password'}
                  </label>
                  <input 
                    id="confirm-password"
                    type="password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none"
                  />
                </div>

                {passwordMessage.text && (
                  <p role="status" className={`text-xs font-bold ${passwordMessage.ok ? 'text-green-600' : 'text-red-500'}`}>
                    {passwordMessage.text}
                  </p>
                )}

                <button 
                  type="submit"
                  disabled={savingPassword}
                  className="px-6 py-2.5 bg-yellow-500 hover:bg-yellow-600 disabled:opacity-50 text-gray-900 font-bold rounded-xl text-sm transition-colors shadow-sm"
                >
                  {isUkr ? 'Змінити пароль' : 'Change Password'}
                </button>
              </form>
            </div>
          )}

          {/* DELETE ACCOUNT */}
          {activeTab === 'delete' && canDeleteAccount && (
            <div className="space-y-4 max-w-md">
              <h2 className="text-xl font-black text-red-600 border-b border-gray-100 dark:border-gray-700 pb-4">
                {isUkr ? 'Видалення акаунта' : 'Delete account'}
              </h2>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {isUkr
                  ? 'Акаунт буде видалено назавжди разом з вашими рецензіями, оцінками, коментарями, списками «До перегляду» і «Переглянуте». Відновити їх неможливо.'
                  : 'The account will be deleted permanently with your reviews, ratings, comments, watchlist and watched list. This cannot be undone.'}
              </p>
              <form onSubmit={handleDeleteAccount} className="space-y-3">
                <label htmlFor="delete-password" className="block text-xs font-bold text-gray-500 uppercase">
                  {isUkr ? 'Пароль для підтвердження' : 'Password to confirm'}
                </label>
                <input
                  id="delete-password"
                  type="password"
                  autoComplete="current-password"
                  value={deletePassword}
                  onChange={(e) => setDeletePassword(e.target.value)}
                  className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:outline-none"
                />
                {deleteError && <p role="alert" className="text-xs font-bold text-red-500">{deleteError}</p>}
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={deleting}
                    className="px-6 py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-bold rounded-xl text-sm transition-colors shadow-sm"
                  >
                    {isUkr ? 'Видалити акаунт назавжди' : 'Delete account permanently'}
                  </button>
                  <button type="button" onClick={() => setActiveTab('general')} className="px-4 py-2.5 text-sm text-gray-600 dark:text-gray-300 hover:underline">
                    {isUkr ? 'Скасувати' : 'Cancel'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* 3. WATCHLIST */}
          {activeTab === 'watchlist' && (
            <div className="space-y-6">
              <h2 className="text-xl font-black text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-4">
                {isUkr ? 'Мій список перегляду (Watchlist)' : 'My Watchlist'}
              </h2>

              {watchlistMovies.length === 0 ? (
                <p className="text-gray-500 dark:text-gray-400 text-sm py-8 text-center">
                  {isUkr ? 'Ваш список обраного порожній.' : 'Your watchlist is empty.'}
                </p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  {watchlistMovies.map(movie => (
                    <div key={movie.id || movie.content_id} className="bg-gray-50 dark:bg-gray-700/40 rounded-2xl p-2 border border-gray-100 dark:border-gray-700 flex flex-col justify-between">
                      <div>
                        <img 
                          src={posterFor(movie, language)}
                          alt={titleOf(movie)}
                          className="w-full h-40 object-cover rounded-xl cursor-pointer hover:opacity-90 transition-opacity"
                          onClick={() => onSelectMovie(movie)}
                        />
                        <button
                          type="button"
                          onClick={() => onSelectMovie(movie)}
                          className="block w-full text-left font-bold text-xs text-gray-900 dark:text-white mt-2 truncate hover:text-yellow-600 dark:hover:text-yellow-400"
                        >
                          {titleOf(movie)}
                        </button>
                        {movie.genre && (
                          <p className="text-[10px] text-gray-500 dark:text-gray-400 truncate">{genreOf(movie)}</p>
                        )}
                      </div>
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-200 dark:border-gray-600">
                        <span className="text-[10px] text-gray-400">{movie.year}</span>
                        <button 
                          onClick={() => onToggleWatchlist(movie.id || movie.content_id)}
                          className="text-xs text-red-500 hover:underline font-bold"
                        >
                          {isUkr ? 'Видалити' : 'Remove'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* WATCHED LIST (FR-006, US-004) */}
          {activeTab === 'watched' && (
            <div className="space-y-6">
              <h2 className="text-xl font-black text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-4">
                {isUkr ? 'Історія переглянутого контенту (Watched List)' : 'Watched Movies & Series'}
              </h2>

              {watchedMovies.length === 0 ? (
                <p className="text-gray-500 dark:text-gray-400 text-sm py-8 text-center">
                  {isUkr ? 'Ви ще не позначили жодного фільму чи серіалу як переглянутий.' : 'You have not marked any movies as watched yet.'}
                </p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  {watchedMovies.map(movie => (
                    <div key={movie.content_id || movie.id} className="bg-gray-50 dark:bg-gray-700/40 rounded-2xl p-2 border border-gray-100 dark:border-gray-700 flex flex-col justify-between">
                      <div>
                        {movie.img && (
                          <img 
                            src={posterFor(movie, language)}
                            alt={titleOf(movie)}
                            className="w-full h-40 object-cover rounded-xl cursor-pointer hover:opacity-90 transition-opacity"
                            onClick={() => onSelectMovie && onSelectMovie(movie)}
                          />
                        )}
                        <button
                          type="button"
                          onClick={() => onSelectMovie && onSelectMovie(movie)}
                          className="block w-full text-left font-bold text-xs text-gray-900 dark:text-white mt-2 truncate hover:text-yellow-600 dark:hover:text-yellow-400"
                        >
                          {titleOf(movie)}
                        </button>
                        {movie.genre && (
                          <p className="text-[10px] text-gray-500 dark:text-gray-400 truncate">{genreOf(movie)}</p>
                        )}
                      </div>
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-200 dark:border-gray-600">
                        <span className="text-[10px] text-gray-400">{movie.year || ''}</span>
                        {onToggleWatched && (
                          <button 
                            onClick={() => onToggleWatched(movie.content_id || movie.id)}
                            className="text-xs text-red-500 hover:underline font-bold"
                          >
                            {isUkr ? 'Зняти позначку' : 'Remove'}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 4. REVIEWS */}
          {activeTab === 'reviews' && (
            <div className="space-y-6">
              <h2 className="text-xl font-black text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-4">
                {isUkr ? 'Мої рецензії та відгуки' : 'My Reviews'}
              </h2>

              {!reviewsLoaded ? (
                <p className="text-gray-500 dark:text-gray-400 text-sm py-8 text-center">{isUkr ? 'Завантаження...' : 'Loading...'}</p>
              ) : reviewsState.error ? (
                <p className="text-red-500 text-sm py-8 text-center">{isUkr ? 'Не вдалося завантажити ваші рецензії.' : 'Failed to load your reviews.'}</p>
              ) : userReviews.length === 0 ? (
                <p className="text-gray-500 dark:text-gray-400 text-sm py-8 text-center">
                  {isUkr ? 'Ви ще не залишили жодної рецензії.' : "You haven't written any reviews yet."}
                </p>
              ) : (
                <div className="space-y-4">
                  {userReviews.map(review => {
                    const reviewedTitle = isUkr
                      ? review.content_title
                      : (review.content_title_en || review.content_title);
                    const poster = posterFor({ img: review.content_img, img_en: review.content_img_en }, language);
                    const titleLabel = reviewedTitle || (isUkr ? 'Фільм' : 'Title');
                    return (
                    <div key={review.review_id} className="p-4 bg-gray-50 dark:bg-gray-700/40 rounded-2xl border border-gray-100 dark:border-gray-700 flex gap-4">
                      {/* The poster and the title open the page of the reviewed title */}
                      <button
                        type="button"
                        onClick={() => openReviewedTitle(review)}
                        // The title button below is the keyboard stop; the poster is an extra target for the mouse
                        tabIndex={-1}
                        aria-label={titleLabel}
                        className="shrink-0 self-start"
                      >
                        {poster ? (
                          <img src={poster} alt="" loading="lazy" className="w-12 aspect-[2/3] object-cover rounded-md shadow-sm hover:ring-2 hover:ring-yellow-500" />
                        ) : (
                          <span className="w-12 aspect-[2/3] rounded-md bg-gray-200 dark:bg-gray-600 flex items-center justify-center text-lg">🎬</span>
                        )}
                      </button>
                      <div className="flex flex-col gap-2 flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-3">
                        <button
                          type="button"
                          onClick={() => openReviewedTitle(review)}
                          className="text-left font-bold text-sm text-gray-900 dark:text-white hover:text-yellow-600 dark:hover:text-yellow-400 hover:underline"
                        >
                          {titleLabel}
                        </button>
                        <span className="shrink-0 px-2.5 py-0.5 bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 rounded-full text-xs font-black">
                          ⭐ {review.rating}/10
                        </span>
                      </div>
                      {review.review_text ? (
                        <p className="text-xs text-gray-600 dark:text-gray-300 italic">"{review.review_text}"</p>
                      ) : (
                        <p className="text-xs text-gray-400">{isUkr ? 'Лише оцінка, без тексту' : 'Rating only'}</p>
                      )}
                      <div className="text-[11px] text-gray-400 mt-1">
                        {new Date(review.created_at).toLocaleDateString(isUkr ? 'uk-UA' : 'en-US')}
                      </div>
                      </div>
                    </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* 5. ACHIEVEMENTS */}
          {activeTab === 'achievements' && (
            <div className="space-y-6">
              <div className="border-b border-gray-100 dark:border-gray-700 pb-4 flex items-center justify-between">
                <h2 className="text-xl font-black text-gray-900 dark:text-white">
                  {isUkr ? 'Ранг і нагороди 🏆' : 'Rank & Achievements 🏆'}
                </h2>
                <span className="text-xs font-bold text-yellow-600 dark:text-yellow-400">
                  {unlockedCount === achievements.length
                    ? (isUkr ? 'Усі медальки розблоковані!' : 'All badges unlocked!')
                    : (isUkr ? `Отримано ${unlockedCount} з ${achievements.length}` : `Unlocked ${unlockedCount} of ${achievements.length}`)}
                </span>
              </div>

              <section aria-labelledby="ranks-heading" className="space-y-3">
                <h3 id="ranks-heading" className="text-sm font-black uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  {isUkr ? 'Ранги' : 'Ranks'}
                </h3>
                <ol className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {RANKS.map(rank => {
                    const reached = rankInfo.xp >= rank.minXp;
                    const current = rank.id === rankInfo.rank.id;
                    const highlighted = `rank-${rank.id}` === highlightAchievement;
                    return (
                      <li
                        key={rank.id}
                        data-testid={`rank-${rank.id}`}
                        data-reached={reached}
                        aria-current={current ? 'step' : undefined}
                        className={`relative p-3 rounded-2xl ring-1 flex items-center gap-3 ${reached ? rank.chip : 'bg-gray-50/60 dark:bg-gray-800/60 text-gray-400 ring-gray-200 dark:ring-gray-700'} ${current ? 'ring-2 shadow-md' : ''} ${highlighted ? 'achievement-highlight' : ''}`}
                      >
                        <span className={`text-2xl ${reached ? '' : 'grayscale opacity-40'}`} aria-hidden="true">{rank.icon}</span>
                        <span className="min-w-0">
                          <span className="block text-xs font-black leading-tight">{rankTitle(rank)}</span>
                          <span className="block text-[10px] font-semibold opacity-80">
                            {current ? (isUkr ? 'Ваш ранг' : 'Your rank') : `${isUkr ? 'від' : 'from'} ${rank.minXp} XP`}
                          </span>
                        </span>
                      </li>
                    );
                  })}
                </ol>
                <p className="text-[11px] text-gray-500 dark:text-gray-400">
                  {isUkr
                    ? `XP: рецензія з текстом +${XP_RULES.textReview}, лише оцінка +${XP_RULES.ratingOnly}, розгорнута рецензія ще +${XP_RULES.detailedBonus}, переглянутий фільм +${XP_RULES.watched}, у «До перегляду» +${XP_RULES.watchlist}.`
                    : `XP: review with text +${XP_RULES.textReview}, rating only +${XP_RULES.ratingOnly}, in-depth review +${XP_RULES.detailedBonus} more, watched title +${XP_RULES.watched}, watchlist title +${XP_RULES.watchlist}.`}
                </p>
              </section>

              <h3 className="text-sm font-black uppercase tracking-wide text-gray-500 dark:text-gray-400">
                {isUkr ? 'Нагороди' : 'Badges'}
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {achievements.map(badge => (
                  <div
                    key={badge.id}
                    data-testid={`badge-${badge.id}`}
                    data-unlocked={badge.unlocked}
                    className={`group relative p-4 rounded-2xl border flex flex-col items-center text-center transition-all shadow-sm ${badge.id === highlightAchievement ? 'achievement-highlight ring-2 ring-yellow-400 ring-offset-2 dark:ring-offset-gray-800 ' : ''}${badge.unlocked ? 'bg-gray-50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-600 hover:border-yellow-500' : 'bg-gray-50/60 dark:bg-gray-800/60 border-dashed border-gray-200 dark:border-gray-700'}`}
                  >
                    <span className={`text-4xl mb-2 filter transition-transform ${badge.unlocked ? 'drop-shadow-md group-hover:scale-110' : 'grayscale opacity-40'}`}>
                      {badge.icon}
                    </span>
                    <h4 className={`text-xs font-bold ${badge.unlocked ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`}>
                      {isUkr ? badge.titleUkr : badge.titleEn}
                    </h4>
                    {badge.unlocked ? (
                      <span className="text-[10px] text-green-600 dark:text-green-400 font-semibold mt-1">
                        {isUkr ? 'Отримано ✓' : 'Unlocked ✓'}
                      </span>
                    ) : (
                      <div className="w-full mt-2">
                        <div className="h-1.5 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                          <div className="h-full bg-yellow-500 rounded-full" style={{ width: `${Math.round((badge.progress / badge.target) * 100)}%` }}></div>
                        </div>
                        <span className="text-[10px] text-gray-500 dark:text-gray-400 font-semibold">
                          {badge.progress} / {badge.target}
                        </span>
                      </div>
                    )}
                    <p className="sr-only">{isUkr ? badge.descUkr : badge.descEn}</p>

                    <div aria-hidden="true" className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 p-2.5 bg-gray-900 text-white text-[11px] rounded-xl shadow-2xl z-50 text-center pointer-events-none">
                      <p className="font-bold mb-0.5 text-yellow-400">{isUkr ? badge.titleUkr : badge.titleEn}</p>
                      <p className="text-gray-300">{isUkr ? badge.descUkr : badge.descEn}</p>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

      </div>

    </div>
  );
}