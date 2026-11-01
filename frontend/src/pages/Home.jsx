import { useState, useEffect } from 'react';
import apiClient from '../api/client';
import MovieCard from '../components/MovieCard';
import { mockMovies } from '../data/mockData';

export default function Home({ selectedCategory, selectedGenre, selectedYear, onSelectMovie, language = 'UKR', watchlist = [], onToggleWatchlist }) {
  const [movies, setMovies] = useState([]);

  // Filters come straight from props (selected in Header via App)
  const filterGenre = selectedGenre || '';
  const filterYear = selectedYear || '';

  // Loading is derived: true until the movies for the current filters are fetched
  const requestKey = `${selectedCategory || ''}|${filterGenre}|${filterYear}`;
  const [loadedKey, setLoadedKey] = useState(null);
  const loading = loadedKey !== requestKey;

  const isUkr = language === 'UKR';

  const genreTranslations = {
    'Бойовик': 'Action',
    'Комедія': 'Comedy',
    'Драма': 'Drama',
    'Фантастика': 'Sci-Fi',
    'Жахи': 'Horror',
    'Трилер': 'Thriller',
    'Детектив': 'Detective',
    'Документальний': 'Documentary',
    'Біографія': 'Biography',
    'Історія': 'History',
    'Мелодрама': 'Romance',
    'Кримінал': 'Crime',
    'Музика': 'Music',
    'Пригоди': 'Adventure'
  };

  const getGenreLabel = (genre) => {
    if (!genre) return '';
    if (isUkr) return genre;
    return genreTranslations[genre] || genre;
  };

  useEffect(() => {
    const params = {};
    if (selectedCategory) {
      const catLower = selectedCategory.toLowerCase();
      if (catLower === 'фільми' || catLower === 'movie' || catLower === 'movies') {
        params.category = 'Movie';
      } else if (catLower === 'серіали' || catLower === 'series' || catLower === 'tv shows') {
        params.category = 'Series';
      } else {
        params.category = selectedCategory;
      }
    }
    if (filterGenre) params.genre = filterGenre;
    if (filterYear) params.year = filterYear;

    // Ignore responses of outdated requests (filters changed while loading)
    let ignore = false;
    apiClient.get('/movies', { params })
      .then(response => {
        if (ignore) return;
        const data = response.data.items || response.data;
        if (data && data.length > 0) {
          setMovies(data);
        } else {
          setMovies(mockMovies);
        }
        setLoadedKey(requestKey);
      })
      .catch(error => {
        if (ignore) return;
        console.warn("Бекенд фільмів ще недоступний, використовуємо mockData.js:", error);
        setMovies(mockMovies);
        setLoadedKey(requestKey);
      });
    return () => {
      ignore = true;
    };
  }, [selectedCategory, filterGenre, filterYear, requestKey]);

  const displayedMovies = movies.filter(movie => {
    if (selectedCategory) {
      const cat = (movie.category || '').toLowerCase();
      const sel = selectedCategory.toLowerCase();
      const isMovie = (sel === 'фільми' || sel === 'movie' || sel === 'movies') && 
                      (cat === 'фільми' || cat === 'movie' || cat === 'movies');
      const isSeries = (sel === 'серіали' || sel === 'series' || sel === 'tv shows') && 
                       (cat === 'серіали' || cat === 'series' || cat === 'tv shows');
      if (!isMovie && !isSeries && cat !== sel) {
        return false;
      }
    }
    
    if (filterGenre) {
      const matchesSingleGenre = movie.genre?.toLowerCase() === filterGenre.toLowerCase();
      const matchesGenresArray = movie.genres?.some(g => g.toLowerCase() === filterGenre.toLowerCase());
      if (!matchesSingleGenre && !matchesGenresArray) return false;
    }

    if (filterYear && movie.year !== Number(filterYear)) {
      return false;
    }

    return true;
  });

  const getCategoryTitle = (cat) => {
    if (!cat) return '';
    if (cat === 'Фільми') return isUkr ? 'фільми' : 'movies';
    if (cat === 'Серіали') return isUkr ? 'серіали' : 'TV shows';
    if (cat === 'Мультфільми') return isUkr ? 'мультфільми' : 'cartoons';
    return cat.toLowerCase();
  };

  const titleText = filterGenre || filterYear || selectedCategory
    ? `${selectedCategory ? getCategoryTitle(selectedCategory) : (isUkr ? 'Фільтри' : 'Filters')} ${filterGenre ? `— ${getGenreLabel(filterGenre)}` : ''} ${filterYear ? `(${filterYear})` : ''}`
    : (isUkr ? 'Нещодавно додані' : 'Recently Added');

  return (
    <section className="py-6">
      {}
      <div className="flex items-center justify-between mb-6 border-b border-gray-100 dark:border-gray-800 pb-4">
        <h2 className="text-xl font-black text-gray-900 dark:text-white border-l-4 border-yellow-500 pl-3 capitalize">
          {titleText}
        </h2>
      </div>
      
      {loading ? (
        <div className="py-12 text-center text-gray-500 text-sm">{isUkr ? 'Завантаження...' : 'Loading...'}</div>
      ) : displayedMovies.length === 0 ? (
        <div className="py-12 text-center">
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            {isUkr ? 'Не знайдено жодного фільму за такими критеріями.' : 'No movies found matching these criteria.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {displayedMovies.map(movie => (
            <MovieCard 
              key={movie.id || movie.content_id} 
              movie={movie} 
              onSelect={onSelectMovie} 
              language={language}
              isWatchlisted={watchlist.includes(movie.id || movie.content_id)}
              onToggleWatchlist={onToggleWatchlist}
            />
          ))}
        </div>
      )}
    </section>
  );
}