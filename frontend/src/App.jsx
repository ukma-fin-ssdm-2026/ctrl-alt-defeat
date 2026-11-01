import { useState, useEffect } from 'react';
import Header from './components/Header';
import Home from './pages/Home';
import MovieDetails from './pages/MovieDetails';
import Recommendations from './components/Recommendations';
import AuthModal from './components/AuthModal';
import UserProfile from './pages/UserProfile';
import { mockMovies } from './data/mockData';
import apiClient from './api/client';
import { getStoredUser, setStoredAuth, clearStoredAuth } from './auth/currentUser';

export default function App() {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  
  const [user, setUser] = useState(() => getStoredUser());
  const isLoggedIn = !!user;

  const [language, setLanguage] = useState('UKR'); 
  
  const [watchlist, setWatchlist] = useState([]);
  const [watchedList, setWatchedList] = useState([]);
  const [catalogMovies, setCatalogMovies] = useState(mockMovies);

  const [selectedMovie, setSelectedMovie] = useState(null);
  const [showProfile, setShowProfile] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedGenre, setSelectedGenre] = useState(null);
  const [selectedYear, setSelectedYear] = useState(null); // Додали стан для року

  const fetchWatchedList = async () => {
    try {
      const res = await apiClient.get('/users/me/watched');
      setWatchedList(res.data.items || []);
    } catch {
      setWatchedList([]);
    }
  };

  useEffect(() => {
    // Validate session on startup with backend via HttpOnly cookie (FR-001, US-011)
    apiClient.get('/auth/me')
      .then(res => {
        setUser(res.data);
        setStoredAuth(null, res.data);
        fetchWatchedList();
      })
      .catch(() => {
        clearStoredAuth();
        setUser(null);
        setWatchedList([]);
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

  const handleGoHome = () => {
    setSelectedMovie(null);
    setShowProfile(false);
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

  const toggleWatchlist = (movieId) => {
    if (!isLoggedIn) {
      setIsAuthOpen(true);
      return;
    }
    setWatchlist(prev => 
      prev.includes(movieId) ? prev.filter(id => id !== movieId) : [...prev, movieId]
    );
  };

  const handleToggleWatched = async (movieOrId) => {
    if (!isLoggedIn) {
      setIsAuthOpen(true);
      return;
    }
    const movieObj = typeof movieOrId === 'object' ? movieOrId : catalogMovies.find(m => (m.id === movieOrId || m.content_id === movieOrId)) || { content_id: movieOrId };
    const contentUuid = movieObj.content_id || movieObj.id;
    const isAlreadyWatched = watchedList.some(item => (item.content_id === contentUuid || item.id === contentUuid));

    if (isAlreadyWatched) {
      try {
        await apiClient.delete(`/users/me/watched/${contentUuid}`);
        setWatchedList(prev => prev.filter(item => item.content_id !== contentUuid && item.id !== contentUuid));
      } catch (e) {
        console.warn("Failed to remove from watched list:", e);
      }
    } else {
      try {
        const res = await apiClient.post('/users/me/watched', { content_id: contentUuid });
        setWatchedList(prev => [res.data, ...prev.filter(item => item.content_id !== contentUuid)]);
      } catch (e) {
        console.warn("Failed to mark as watched:", e);
      }
    }
  };

  const handleLogin = async (email, password) => {
    try {
      const response = await apiClient.post('/auth/login', { email, password });
      const { access_token, user: userData } = response.data;
      setStoredAuth(access_token, userData);
      setUser(userData);
      setIsAuthOpen(false);
      fetchWatchedList();
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
    setWatchlist([]);
    setWatchedList([]);
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
        onGoProfile={() => { setSelectedMovie(null); setShowProfile(true); }}
        
        language={language}
        onToggleLanguage={() => setLanguage(l => l === 'UKR' ? 'EN' : 'UKR')}
        movies={catalogMovies}
        onSelectMovie={(movie) => { setShowProfile(false); setSelectedMovie(movie); }}
        
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
        {showProfile && user ? (
          <UserProfile 
            user={user}
            language={language}
            watchlistMovies={catalogMovies.filter(m => watchlist.includes(m.id || m.content_id))}
            watchedMovies={watchedList}
            onSelectMovie={(movie) => { setShowProfile(false); setSelectedMovie(movie); }}
            onToggleWatchlist={toggleWatchlist}
            onToggleWatched={handleToggleWatched}
            onDeleteProfile={() => {
               setUser(null); setWatchlist([]); setWatchedList([]); handleGoHome(); 
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
            isWatchlisted={watchlist.includes(selectedMovie.id)}
            onToggleWatchlist={() => toggleWatchlist(selectedMovie.id)}
            isWatched={watchedList.some(item => (item.content_id || item.id) === (selectedMovie.content_id || selectedMovie.id))}
            onToggleWatched={() => handleToggleWatched(selectedMovie)}
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
        © 2026 Rotten Eggs. Усі права захищено.
      </footer>

      {isAuthOpen && (
        <AuthModal 
          close={() => setIsAuthOpen(false)} 
          onLogin={handleLogin} 
        />
      )}
    </div>
  );
}