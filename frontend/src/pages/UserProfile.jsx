import { useEffect, useState } from 'react';
import apiClient from '../api/client';
import { getDisplayName } from '../utils/displayName';

export default function UserProfile({ 
  user, 
  language, 
  watchlistMovies, 
  watchedMovies = [],
  onSelectMovie, 
  onToggleWatchlist, 
  onToggleWatched,
  onDeleteProfile 
}) {
  const [activeTab, setActiveTab] = useState('general'); // 'general', 'security', 'watchlist', 'watched', 'reviews', 'achievements'
  
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
  const userReviews = reviewsLoaded ? reviewsState.items : [];

  const achievements = [
    { 
      id: 1, 
      icon: '🥇', 
      titleUkr: 'Легендарний рецензент', 
      titleEn: 'Legendary Reviewer', 
      descUkr: 'Написано понад 10 детальних рецензій', 
      descEn: 'Written over 10 detailed reviews',
      unlocked: true 
    },
    { 
      id: 2, 
      icon: '🔥', 
      titleUkr: 'Людина-лайк', 
      titleEn: 'Like Magnet', 
      descUkr: 'Ваші рецензії отримали понад 100 вподобайок', 
      descEn: 'Your reviews received over 100 likes',
      unlocked: true 
    },
    { 
      id: 3, 
      icon: '🎬', 
      titleUkr: 'Кіноман', 
      titleEn: 'Cinephile', 
      descUkr: 'Додано понад 20 фільмів до списку перегляду', 
      descEn: 'Added over 20 movies to your watchlist',
      unlocked: true 
    },
    { 
      id: 4, 
      icon: '⭐', 
      titleUkr: 'Експерт року', 
      titleEn: 'Expert of the Year', 
      descUkr: 'Активна участь у житті спільноти «Після титрів»', 
      descEn: 'Active participation in the After Credits community',
      unlocked: true 
    },
    { 
      id: 5, 
      icon: '🛡️', 
      titleUkr: 'Ветеран платформи', 
      titleEn: 'Platform Veteran', 
      descUkr: 'Реєстрація серед перших користувачів сервісу', 
      descEn: 'Registered among the first users',
      unlocked: true 
    },
    { 
      id: 6, 
      icon: '💎', 
      titleUkr: 'Критик вищої категорії', 
      titleEn: 'Top Critic', 
      descUkr: 'Точність оцінок збігається з рейтингом IMDb на 95%', 
      descEn: 'Review accuracy matches IMDb rating by 95%',
      unlocked: true 
    }
  ];

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
          <div className="inline-flex items-center gap-2 mt-3 px-3 py-1 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 rounded-full text-xs font-bold">
            <span>🏆</span> {isUkr ? 'Ранг: Кіноексперт' : 'Rank: Movie Expert'}
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
            <span>🏆</span> {isUkr ? 'Нагороди' : 'Achievements'} <span className="ml-auto text-xs px-2 py-0.5 bg-yellow-400 text-gray-900 rounded-full font-black">{achievements.length}</span>
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
                  <p className="text-base font-bold text-gray-800 dark:text-gray-100 mt-1">Жовтень 2026</p>
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
                          src={movie.img} 
                          alt={movie.title} 
                          className="w-full h-40 object-cover rounded-xl cursor-pointer hover:opacity-90 transition-opacity"
                          onClick={() => onSelectMovie(movie)}
                        />
                        <h4 className="font-bold text-xs text-gray-900 dark:text-white mt-2 truncate">{movie.title}</h4>
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
                            src={movie.img} 
                            alt={movie.title || 'Movie'} 
                            className="w-full h-40 object-cover rounded-xl cursor-pointer hover:opacity-90 transition-opacity"
                            onClick={() => onSelectMovie && onSelectMovie(movie)}
                          />
                        )}
                        <h4 className="font-bold text-xs text-gray-900 dark:text-white mt-2 truncate">
                          {isUkr ? movie.title : (movie.title_en || movie.title)}
                        </h4>
                        {movie.genre && (
                          <p className="text-[10px] text-gray-500 dark:text-gray-400 truncate">{movie.genre}</p>
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
                  {userReviews.map(review => (
                    <div key={review.review_id} className="p-4 bg-gray-50 dark:bg-gray-700/40 rounded-2xl border border-gray-100 dark:border-gray-700 flex flex-col gap-2">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-sm text-gray-900 dark:text-white">{review.content_title || (isUkr ? 'Фільм' : 'Title')}</h4>
                        <span className="px-2.5 py-0.5 bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 rounded-full text-xs font-black">
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
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 5. ACHIEVEMENTS */}
          {activeTab === 'achievements' && (
            <div className="space-y-6">
              <div className="border-b border-gray-100 dark:border-gray-700 pb-4 flex items-center justify-between">
                <h2 className="text-xl font-black text-gray-900 dark:text-white">
                  {isUkr ? 'Нагороди та досягнення 🏆' : 'Badges & Achievements 🏆'}
                </h2>
                <span className="text-xs font-bold text-yellow-600 dark:text-yellow-400">
                  {isUkr ? 'Усі медальки розблоковані!' : 'All badges unlocked!'}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {achievements.map(badge => (
                  <div 
                    key={badge.id}
                    className="group relative p-4 bg-gray-50 dark:bg-gray-700/50 rounded-2xl border border-gray-200 dark:border-gray-600 flex flex-col items-center text-center cursor-pointer hover:border-yellow-500 transition-all shadow-sm"
                  >
                    <span className="text-4xl mb-2 filter drop-shadow-md group-hover:scale-110 transition-transform">
                      {badge.icon}
                    </span>
                    <h4 className="text-xs font-bold text-gray-900 dark:text-white">
                      {isUkr ? badge.titleUkr : badge.titleEn}
                    </h4>
                    <span className="text-[10px] text-green-600 dark:text-green-400 font-semibold mt-1">
                      {isUkr ? 'Отримано ✓' : 'Unlocked ✓'}
                    </span>

                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 p-2.5 bg-gray-900 text-white text-[11px] rounded-xl shadow-2xl z-50 text-center pointer-events-none">
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