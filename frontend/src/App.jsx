import { useState, useEffect } from 'react';
import Header from './components/Header';
import Home from './pages/Home';
import MovieDetails from './pages/MovieDetails';
import AuthModal from './components/AuthModal';
import UserProfile from './pages/UserProfile';
import { mockMovies } from './data/mockData';

export default function App() {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  
  const [user, setUser] = useState(null);
  const isLoggedIn = !!user;

  const [language, setLanguage] = useState('UKR'); 
  
  const [watchlist, setWatchlist] = useState([]);

  const [selectedMovie, setSelectedMovie] = useState(null);
  const [showProfile, setShowProfile] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedGenre, setSelectedGenre] = useState(null);
  const [selectedYear, setSelectedYear] = useState(null); // Додали стан для року

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

  const handleResetFilters = () => {
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

  const handleLogin = (email, password) => {
    if (email === 'admin@gmail.com' && password === 'password12345') {
      setUser({ username: 'admin', email: 'admin@gmail.com' });
      setIsAuthOpen(false);
      return true;
    }
    return false;
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300 flex flex-col">
      <Header 
        toggleTheme={() => setIsDarkMode(!isDarkMode)} 
        isDarkMode={isDarkMode}
        openAuth={() => setIsAuthOpen(true)}
        user={user}
        onLogout={() => { setUser(null); setWatchlist([]); handleGoHome(); }}
        onGoHome={handleGoHome}
        onGoProfile={() => { setSelectedMovie(null); setShowProfile(true); }}
        
        language={language}
        onToggleLanguage={() => setLanguage(l => l === 'UKR' ? 'EN' : 'UKR')}
        movies={mockMovies}
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
            watchlistMovies={mockMovies?.filter(m => watchlist.includes(m.id)) || []}
            onSelectMovie={(movie) => { setShowProfile(false); setSelectedMovie(movie); }}
            onToggleWatchlist={toggleWatchlist}
            onDeleteProfile={() => {
               setUser(null); setWatchlist([]); handleGoHome(); 
               alert(language === 'UKR' ? 'Профіль видалено' : 'Profile deleted');
            }}
          />
        ) : selectedMovie ? (
          <MovieDetails 
            movie={selectedMovie} 
            isLoggedIn={isLoggedIn}
            openAuth={() => setIsAuthOpen(true)}
            onBack={() => setSelectedMovie(null)}
            language={language}
            isWatchlisted={watchlist.includes(selectedMovie.id)}
            onToggleWatchlist={() => toggleWatchlist(selectedMovie.id)}
          />
        ) : (
          <Home 
            selectedCategory={selectedCategory}
            selectedGenre={selectedGenre} 
            selectedYear={selectedYear}
            onSelectMovie={(movie) => setSelectedMovie(movie)} 
            language={language}
            watchlist={watchlist}
            onToggleWatchlist={toggleWatchlist}
          />
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