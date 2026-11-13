import { useState, useEffect } from 'react';
import Header from './components/Header';
import Home from './pages/Home';
import MovieDetails from './pages/MovieDetails';
import Recommendations from './components/Recommendations';
import AuthModal from './components/AuthModal';
import UserProfile from './pages/UserProfile';
import AdminUsers from './pages/AdminUsers';
import AdminCatalogSync from './components/AdminCatalogSync';
import AchievementToast from './components/AchievementToast';
import apiClient, { SESSION_EXPIRED_EVENT } from './api/client';
import { fetchWholeCatalog } from './api/catalog';
import { getStoredUser, setStoredAuth, clearStoredAuth } from './auth/currentUser';
import useWatchlist from './hooks/useWatchlist';
import useWatchedList from './hooks/useWatchedList';
import useUserReviews from './hooks/useUserReviews';
import useAchievementNotifications from './hooks/useAchievementNotifications';
import useViewHistory from './hooks/useViewHistory';
import { readDarkMode, readLanguage, saveDarkMode, saveLanguage } from './utils/preferences';

export default function App() {
  // Theme and language are remembered in this browser (the theme follows the system setting until chosen)
  const [isDarkMode, setIsDarkMode] = useState(readDarkMode);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  
  const [user, setUser] = useState(() => getStoredUser());
  const isLoggedIn = !!user;

  const [language, setLanguage] = useState(readLanguage);
  const isUkr = language === 'UKR';
  const [catalogMovies, setCatalogMovies] = useState([]);

  // Message shown in the login window when a guest uses a members-only feature
  const [authNotice, setAuthNotice] = useState('');
  const closeAuth = () => { setIsAuthOpen(false); setAuthNotice(''); };

  const requireAuth = () => {
    setAuthNotice(isUkr
      ? 'Будь ласка, авторизуйтесь для використання цієї функції'
      : 'Please log in to use this feature');
    setIsAuthOpen(true);
  };

  // Watched list stored on the backend (FR-006)
  const {
    watchedMovies,
    loaded: watchedLoaded,
    isWatched,
    toggleWatched,
    error: watchedError,
    clearError: clearWatchedError,
  } = useWatchedList({ user, catalog: catalogMovies, onAuthRequired: requireAuth });

  // Watchlist stored on the backend (FR-005)
  const {
    watchlistIds: watchlist,
    watchlistMovies,
    loaded: watchlistLoaded,
    toggleWatchlist,
    error: watchlistError,
    clearError: clearWatchlistError,
  } = useWatchlist({
    user,
    catalog: catalogMovies,
    onAuthRequired: requireAuth,
  });

  // One message for failed list updates (watchlist or watched)
  const listError = watchlistError || watchedError;
  const clearListError = () => { clearWatchlistError(); clearWatchedError(); };

  // Profile achievements: notify about newly unlocked badges anywhere on the site
  const { reviews: userReviews, loaded: reviewsLoaded, refresh: refreshUserReviews } = useUserReviews({ user });
  const achievementToast = useAchievementNotifications({
    user,
    reviews: userReviews,
    watched: watchedMovies,
    watchlist: watchlistMovies,
    ready: reviewsLoaded && watchedLoaded && watchlistLoaded,
  });
  // Which profile tab to open and which badge to highlight ("View" in the pop-up)
  const [profileTarget, setProfileTarget] = useState({ tab: 'general', highlight: null, visit: 0 });

  // The page shown (home with filters, a movie, the profile, the admin page) lives in the browser history:
  // the Back button returns to the previous page and a reload keeps the current one
  const { view, navigate, goBack } = useViewHistory();
  const {
    movie: selectedMovie,
    profile: showProfile,
    admin: showAdmin,
    category: selectedCategory,
    genre: selectedGenre,
    year: selectedYear,
  } = view;
  const filters = { category: selectedCategory, genre: selectedGenre, year: selectedYear };
  // A movie opens on top of the current filters, so "Back" returns to the same list
  const openMovie = movie => navigate({ ...filters, movie });

  // FR-001: the activation link from the email opens /verify-email?token=...
  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token');
    if (window.location.pathname !== '/verify-email' || !token) return;
    apiClient.get('/auth/verify', { params: { token } })
      .then(() => setAuthNotice('Пошту підтверджено! Тепер ви можете увійти.'))
      .catch(error => setAuthNotice(error.response?.data?.error?.code === 'VERIFICATION_TOKEN_EXPIRED'
        ? 'Посилання застаріло (діє 24 години). Увійдіть з вашою поштою, щоб надіслати новий лист.'
        : 'Посилання недійсне або вже використане. Увійдіть або надішліть лист ще раз.'))
      .finally(() => {
        setIsAuthOpen(true);
        // Keep the page state of the history entry, only drop the token from the address
        window.history.replaceState(window.history.state, '', '/');
      });
  }, []);

  useEffect(() => {
    // Validate session on startup with backend via HttpOnly cookie (FR-001, US-011)
    apiClient.get('/auth/me')
      .then(res => {
        setUser(res.data);
        setStoredAuth(null, res.data);
      })
      .catch(() => {
        clearStoredAuth();
        setUser(null);
      });

    // The whole catalog (several pages of 100): header search and the user lists need every title
    fetchWholeCatalog()
      .then(items => {
        setCatalogMovies(items);
      })
      .catch(err => {
        console.warn("Каталог недоступний:", err);
      });
  }, []);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    saveDarkMode(isDarkMode);
  }, [isDarkMode]);

  useEffect(() => {
    saveLanguage(language);
    document.documentElement.lang = language === 'UKR' ? 'uk' : 'en';
  }, [language]);

  // The server rejected the session (expired token, page reload without cookie): log out visibly
  useEffect(() => {
    const onSessionExpired = () => {
      clearStoredAuth();
      setUser(null);
      setAuthNotice(language === 'UKR'
        ? 'Сесія завершилась. Будь ласка, увійдіть знову.'
        : 'Your session has expired. Please log in again.');
      setIsAuthOpen(true);
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
  }, [language]);

  const handleGoHome = () => navigate({});

  const handleApplyFilter = (category, genre, year) => {
    navigate({ category: category || null, genre: genre || null, year: year ? Number(year) : null });
  };

  const openProfile = (tab = 'general', highlight = null) => {
    setProfileTarget(current => ({ tab, highlight, visit: current.visit + 1 }));
    navigate({ profile: true });
  };

  const handleLogin = async (email, password) => {
    try {
      const response = await apiClient.post('/auth/login', { email, password });
      const { access_token, user: userData } = response.data;
      setStoredAuth(access_token, userData);
      setUser(userData);
      closeAuth();
      return { success: true };
    } catch (err) {
      const errCode = err.response?.data?.error?.code || err.response?.data?.detail?.code;
      const errMsg = err.response?.data?.error?.message || err.response?.data?.detail?.message || err.message;
      return { success: false, code: errCode, message: errMsg };
    }
  };

  const handleLogout = async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      console.warn("Logout error:", e);
    }
    clearStoredAuth();
    setUser(null);
    handleGoHome();
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300 flex flex-col">
      <Header 
        toggleTheme={() => setIsDarkMode(!isDarkMode)} 
        isDarkMode={isDarkMode}
        openAuth={() => setIsAuthOpen(true)}
        user={user}
        onLogout={handleLogout}
        onGoHome={handleGoHome}
        onGoProfile={() => openProfile()}
        onGoAdmin={() => navigate({ admin: true })}
        
        language={language}
        onToggleLanguage={() => setLanguage(l => l === 'UKR' ? 'EN' : 'UKR')}
        movies={catalogMovies}
        onSelectMovie={movie => navigate({ movie })}
        
        onSelectCategory={category => navigate({ category })}
        onSelectGenre={(category, genre) => navigate({ category, genre })}
        onApplyFilter={handleApplyFilter}
      />
      
      <main className="container mx-auto px-4 flex-1 py-6">
        {showAdmin && user?.role === 'admin' ? (
          <>
            <AdminCatalogSync language={language} />
            <AdminUsers language={language} />
          </>
        ) : showProfile && user ? (
          <UserProfile 
            key={profileTarget.visit}
            initialTab={profileTarget.tab}
            highlightAchievement={profileTarget.highlight}
            user={user}
            language={language}
            watchlistMovies={watchlistMovies}
            watchedMovies={watchedMovies}
            onSelectMovie={movie => navigate({ movie })}
            onToggleWatchlist={toggleWatchlist}
            onToggleWatched={toggleWatched}
            onDeleteProfile={() => {
              // The server already removed the account and cleared the session cookie
              clearStoredAuth();
              setUser(null);
              handleGoHome();
              setAuthNotice(language === 'UKR' ? 'Акаунт видалено.' : 'The account was deleted.');
              setIsAuthOpen(true);
            }}
          />
        ) : selectedMovie ? (
          <MovieDetails 
            movie={selectedMovie} 
            user={user}
            isLoggedIn={isLoggedIn}
            openAuth={() => setIsAuthOpen(true)}
            onBack={goBack}
            onSelectMovie={openMovie}
            language={language}
            isWatchlisted={watchlist.includes(selectedMovie.id || selectedMovie.content_id)}
            onToggleWatchlist={() => toggleWatchlist(selectedMovie)}
            isWatched={isWatched(selectedMovie)}
            onToggleWatched={() => toggleWatched(selectedMovie)}
            onReviewsChanged={refreshUserReviews}
          />
        ) : (
          <>
            {/* FR-007: personal block only on the unfiltered home page */}
            {!selectedCategory && !selectedGenre && !selectedYear && (
              <Recommendations
                user={user}
                isLoggedIn={isLoggedIn}
                openAuth={() => setIsAuthOpen(true)}
                onSelectMovie={openMovie}
                language={language}
                watchlist={watchlist}
                onToggleWatchlist={toggleWatchlist}
              />
            )}
            <Home 
            selectedCategory={selectedCategory}
            selectedGenre={selectedGenre} 
            selectedYear={selectedYear}
            onSelectMovie={openMovie}
            language={language}
            watchlist={watchlist}
            onToggleWatchlist={toggleWatchlist}
          />
          </>
        )}
      </main>

      <footer className="border-t border-gray-200 dark:border-gray-800 py-6 text-center text-xs text-gray-500 dark:text-gray-400 mt-12">
        <p>© 2026 Після титрів. Усі права захищено.</p>
        {/* Attribution required by the TMDB API terms of use */}
        <div className="mt-3 flex flex-col items-center gap-1.5">
          {/* Official TMDB logo, unchanged and smaller than our own logo */}
          <a href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer" aria-label="The Movie Database (TMDB)">
            <img src="/tmdb-logo.svg" alt="The Movie Database (TMDB)" className="h-3 w-auto" />
          </a>
          <p>
            {isUkr ? 'Дані про фільми та постери надає TMDB. ' : 'Movie data and posters are provided by TMDB. '}
            This product uses the TMDB API but is not endorsed or certified by TMDB.
          </p>
        </div>
      </footer>

      {listError && (
        <div role="alert" className="fixed bottom-4 right-4 z-40 max-w-sm bg-red-50 dark:bg-red-900/80 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-100 text-sm px-4 py-3 rounded-xl shadow-lg flex items-start gap-3">
          <span>
            {listError === 'UNAVAILABLE'
              ? (isUkr ? 'Цей фільм зараз не можна додати: каталог недоступний (сервер не відповідає).' : 'This title cannot be added right now: the catalog is unavailable (server is not responding).')
              : (isUkr ? 'Не вдалося оновити список. Спробуйте ще раз.' : 'Failed to update the list. Please try again.')}
          </span>
          <button onClick={clearListError} aria-label={isUkr ? 'Закрити' : 'Close'} className="font-bold">✕</button>
        </div>
      )}

      {user && (
        <AchievementToast
          badge={achievementToast.current}
          pending={achievementToast.pending}
          language={language}
          onClose={achievementToast.dismiss}
          onView={badge => {
            achievementToast.dismiss();
            openProfile('achievements', badge.id);
            window.scrollTo?.({ top: 0, behavior: 'smooth' });
          }}
        />
      )}

      {isAuthOpen && (
        <AuthModal 
          close={closeAuth} 
          onLogin={handleLogin} 
          language={language}
          notice={authNotice}
        />
      )}
    </div>
  );
}