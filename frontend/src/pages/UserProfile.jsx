import { useState } from 'react';

export default function UserProfile({ 
  user, 
  language, 
  watchlistMovies, 
  onSelectMovie, 
  onToggleWatchlist, 
  onDeleteProfile 
}) {
  const [activeTab, setActiveTab] = useState('general'); // 'general', 'security', 'watchlist', 'reviews', 'achievements'
  
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordMessage, setPasswordMessage] = useState('');

  const isUkr = language === 'UKR';

  const [userReviews] = useState([
    { id: 1, movieTitle: 'Інстеллар / Interstellar', rating: 10, text: 'Неймовірний фільм із геніальною музикою Ганса Циммера!', likes: 52 },
    { id: 2, movieTitle: 'Темний лицар / The Dark Knight', rating: 9, text: 'Гітлер Леджер у ролі Джокера — це шедевр на всі часи.', likes: 38 },
    { id: 3, movieTitle: 'Оппенгеймер / Oppenheimer', rating: 8, text: 'Потужна драма, Кілліан Мерфі неперевершений.', likes: 14 }
  ]);

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
      descUkr: 'Активна участь у житті спільноти Rotten Eggs', 
      descEn: 'Active participation in Rotten Eggs community',
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

  const handlePasswordChange = (e) => {
    e.preventDefault();
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordMessage(isUkr ? 'Заповніть усі поля!' : 'Fill in all fields!');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordMessage(isUkr ? 'Нові паролі не збігаються!' : 'New passwords do not match!');
      return;
    }
    setPasswordMessage(isUkr ? 'Пароль успішно змінено!' : 'Password successfully changed!');
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      
      {/* Шапка профілю */}
      <div className="bg-white dark:bg-gray-800 rounded-3xl p-6 shadow-xl border border-gray-100 dark:border-gray-700 flex flex-col sm:flex-row items-center gap-6 mb-8">
        <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-yellow-500 to-amber-300 flex items-center justify-center text-4xl font-black text-gray-900 shadow-inner">
          {user?.username?.[0]?.toUpperCase() || 'U'}
        </div>
        <div className="text-center sm:text-left flex-1">
          <h1 className="text-2xl font-black text-gray-900 dark:text-white">
            {user?.username || 'Користувач'}
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

          <div className="pt-3 mt-3 border-t border-gray-100 dark:border-gray-700">
            <button 
              onClick={onDeleteProfile}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
            >
              <span>🗑️</span> {isUkr ? 'Видалити акаунт' : 'Delete Account'}
            </button>
          </div>

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
                  <p className="text-base font-bold text-gray-800 dark:text-gray-100 mt-1">{user?.username}</p>
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
                  <label className="block text-xs font-bold text-gray-500 uppercase mb-1">
                    {isUkr ? 'Поточний пароль' : 'Current Password'}
                  </label>
                  <input 
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase mb-1">
                    {isUkr ? 'Новий пароль' : 'New Password'}
                  </label>
                  <input 
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase mb-1">
                    {isUkr ? 'Підтвердіть новий пароль' : 'Confirm New Password'}
                  </label>
                  <input 
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none"
                  />
                </div>

                {passwordMessage && (
                  <p className={`text-xs font-bold ${passwordMessage.includes('успішно') || passwordMessage.includes('successfully') ? 'text-green-600' : 'text-red-500'}`}>
                    {passwordMessage}
                  </p>
                )}

                <button 
                  type="submit"
                  className="px-6 py-2.5 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold rounded-xl text-sm transition-colors shadow-sm"
                >
                  {isUkr ? 'Змінити пароль' : 'Change Password'}
                </button>
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

          {/* 4. REVIEWS */}
          {activeTab === 'reviews' && (
            <div className="space-y-6">
              <h2 className="text-xl font-black text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-4">
                {isUkr ? 'Мої рецензії та відгуки' : 'My Reviews'}
              </h2>

              <div className="space-y-4">
                {userReviews.map(review => (
                  <div key={review.id} className="p-4 bg-gray-50 dark:bg-gray-700/40 rounded-2xl border border-gray-100 dark:border-gray-700 flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-sm text-gray-900 dark:text-white">{review.movieTitle}</h4>
                      <span className="px-2.5 py-0.5 bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 rounded-full text-xs font-black">
                        ⭐ {review.rating}/10
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 dark:text-gray-300 italic">"{review.text}"</p>
                    <div className="flex items-center gap-2 text-[11px] text-gray-400 mt-1">
                      <span>❤️ {review.likes} {isUkr ? 'вподобайок' : 'likes'}</span>
                    </div>
                  </div>
                ))}
              </div>
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