import { useState, useEffect } from 'react';
import Header from './components/Header';
import Home from './pages/Home';
import MovieDetails from './pages/MovieDetails';
import Recommendations from './components/Recommendations';
import AuthModal from './components/AuthModal';
import UserProfile from './pages/UserProfile';
import AdminUsers from './pages/AdminUsers';
import { mockMovies } from './data/mockData';
import apiClient, { SESSION_EXPIRED_EVENT } from './api/client';
import { getStoredUser, setStoredAuth, clearStoredAuth } from './auth/currentUser';
import useWatchlist from './hooks/useWatchlist';
import useWatchedList from './hooks/useWatchedList';

export default function App() {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  
  const [user, setUser] = useState(() => getStoredUser());
  const isLoggedIn = !!user;

  const [language, setLanguage] = useState('UKR'); 
  const isUkr = language === 'UKR';
  const [catalogMovies, setCatalogMovies] = useState(mockMovies);

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
    isWatched,
    toggleWatched,
    error: watchedError,
    clearError: clearWatchedError,
  } = useWatchedList({ user, catalog: catalogMovies, onAuthRequired: requireAuth });

  // Watchlist stored on the backend (FR-005)
  const {
    watchlistIds: watchlist,
    watchlistMovies,
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

  const [selectedMovie, setSelectedMovie] = useState(null);
  const [showProfile, setShowProfile] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedGenre, setSelectedGenre] = useState(null);
  const [selectedYear, setSelectedYear] = useState(null); // Додали стан для року

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

    apiClient.get('/movies', { params: { limit: 100 } })
      .then(response => {
        const items = response.data.items || response.data;
        if (items && items.length > 0) {
          setCatalogMovies(items);
        }
      })
      .catch(err => {
        console.warn("Бекенд каталогу недоступний у App.jsx, залишаємо mockData:", err);
      });
  }, []);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

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

  const handleGoHome = () => {
    setSelectedMovie(null);
    setShowProfile(false);
    setShowAdmin(false);
    setSelectedCategory(null);
    setSelectedGenre(null);
    setSelectedYear(null);
  };

  const handleApplyFilter = (category, genre, year) => {
    handleGoHome();
    setSelectedCategory(category);
    if (genre) setSelectedGenre(genre);
    if (year) setSelectedYear(Number(year));
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
        onGoProfile={() => { setSelectedMovie(null); setShowAdmin(false); setShowProfile(true); }}
        onGoAdmin={() => { setSelectedMovie(null); setShowProfile(false); setShowAdmin(true); }}
        
        language={language}
        onToggleLanguage={() => setLanguage(l => l === 'UKR' ? 'EN' : 'UKR')}
        movies={catalogMovies}
        onSelectMovie={(movie) => { setShowProfile(false); setShowAdmin(false); setSelectedMovie(movie); }}
        
        onSelectCategory={(category) => {
          handleGoHome();
          setSelectedCategory(category);
        }}
        onSelectGenre={(category, genre) => {
          handleGoHome();
          setSelectedCategory(category);
          setSelectedGenre(genre);
        }}
        onApplyFilter={handleApplyFilter}
      />
      
      <main className="container mx-auto px-4 flex-1 py-6">
        {showAdmin && user?.role === 'admin' ? (
          <AdminUsers language={language} />
        ) : showProfile && user ? (
          <UserProfile 
            user={user}
            language={language}
            watchlistMovies={watchlistMovies}
            watchedMovies={watchedMovies}
            onSelectMovie={(movie) => { setShowProfile(false); setSelectedMovie(movie); }}
            onToggleWatchlist={toggleWatchlist}
            onToggleWatched={toggleWatched}
            onDeleteProfile={() => {
               setUser(null); handleGoHome(); 
               alert(language === 'UKR' ? 'Профіль видалено' : 'Profile deleted');
            }}
          />
        ) : selectedMovie ? (
          <MovieDetails 
            movie={selectedMovie} 
            user={user}
            isLoggedIn={isLoggedIn}
            openAuth={() => setIsAuthOpen(true)}
            onBack={() => setSelectedMovie(null)}
            language={language}
            isWatchlisted={watchlist.includes(selectedMovie.id || selectedMovie.content_id)}
            onToggleWatchlist={() => toggleWatchlist(selectedMovie)}
            isWatched={isWatched(selectedMovie)}
            onToggleWatched={() => toggleWatched(selectedMovie)}
          />
        ) : (
          <>
            {/* FR-007: personal block only on the unfiltered home page */}
            {!selectedCategory && !selectedGenre && !selectedYear && (
              <Recommendations
                user={user}
                isLoggedIn={isLoggedIn}
                openAuth={() => setIsAuthOpen(true)}
                onSelectMovie={(movie) => setSelectedMovie(movie)}
                language={language}
                watchlist={watchlist}
                onToggleWatchlist={toggleWatchlist}
              />
            )}
            <Home 
            selectedCategory={selectedCategory}
            selectedGenre={selectedGenre} 
            selectedYear={selectedYear}
            onSelectMovie={(movie) => setSelectedMovie(movie)} 
            language={language}
            watchlist={watchlist}
            onToggleWatchlist={toggleWatchlist}
          />
          </>
        )}
      </main>

      <footer className="border-t border-gray-200 dark:border-gray-800 py-6 text-center text-xs text-gray-500 dark:text-gray-400 mt-12">
        © 2026 Після титрів. Усі права захищено.
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