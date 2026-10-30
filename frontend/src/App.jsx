import { useState, useEffect } from 'react';
import Header from './components/Header';
import Home from './pages/Home';
import MovieDetails from './pages/MovieDetails';
import AuthModal from './components/AuthModal';

export default function App() {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedGenre, setSelectedGenre] = useState(null);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const handleGoHome = () => {
    setSelectedMovie(null);
    setSelectedCategory(null);
    setSelectedGenre(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300 flex flex-col">
      <Header 
        toggleTheme={() => setIsDarkMode(!isDarkMode)} 
        isDarkMode={isDarkMode}
        openAuth={() => setIsAuthOpen(true)}
        onGoHome={handleGoHome}
        onSelectCategory={(category) => {
          setSelectedMovie(null);
          setSelectedCategory(category);
          setSelectedGenre(null);
        }}
        onSelectGenre={(category, genre) => {
          setSelectedMovie(null);
          setSelectedCategory(category);
          setSelectedGenre(genre);
        }}
      />
      
      <main className="container mx-auto px-4 flex-1">
        {selectedMovie ? (
          <MovieDetails 
            movie={selectedMovie} 
            isLoggedIn={isLoggedIn}
            openAuth={() => setIsAuthOpen(true)}
            onBack={() => setSelectedMovie(null)}
          />
        ) : (
          <Home 
            selectedCategory={selectedCategory}
            selectedGenre={selectedGenre} 
            onSelectMovie={(movie) => setSelectedMovie(movie)} 
          />
        )}
      </main>

      <footer className="border-t border-gray-200 dark:border-gray-800 py-6 text-center text-xs text-gray-500 dark:text-gray-400 mt-12">
        © 2026 Rotten Eggs. Усі права захищено.
      </footer>

      {isAuthOpen && (
        <AuthModal 
          close={() => setIsAuthOpen(false)} 
          onLoginSuccess={() => setIsLoggedIn(true)}
        />
      )}
    </div>
  );
}