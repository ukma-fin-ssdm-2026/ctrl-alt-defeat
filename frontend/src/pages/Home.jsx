import { useState, useEffect } from 'react';
import { fetchWholeCatalog } from '../api/catalog';
import MovieCard from '../components/MovieCard';
import { SORT_OPTIONS, sortMovies } from '../utils/sortMovies';
import { translateGenre } from '../utils/genres';
import { buildCatalogParams } from '../utils/catalogParams';

export default function Home({ selectedCategory, selectedGenre, selectedYear, onSelectMovie, language = 'UKR', watchlist = [], onToggleWatchlist }) {
  const [movies, setMovies] = useState([]);
  // The catalog could not be loaded (server unavailable)
  const [loadError, setLoadError] = useState(false);

  // Filters come straight from props (selected in Header via App)
  const filterGenre = selectedGenre || '';
  const filterYear = selectedYear || '';

  // Sorting (FR-010)
  const [sortKey, setSortKey] = useState('');

  // Loading is derived: true until the movies for the current filters are fetched.
  // Sorting is not part of this key: the current list is re-sorted instantly while fresh data loads.
  const requestKey = `${selectedCategory || ''}|${filterGenre}|${filterYear}`;
  const [loadedKey, setLoadedKey] = useState(null);
  const loading = loadedKey !== requestKey;

  const isUkr = language === 'UKR';

  const getGenreLabel = (genre) => translateGenre(genre, isUkr ? 'UKR' : 'EN');

  // Every matching title at once (page by page from the API): the list keeps working after going back
  useEffect(() => {
    const params = buildCatalogParams({ selectedCategory, filterGenre, filterYear, sortKey });

    // Ignore responses of outdated requests (filters changed while loading)
    let ignore = false;
    fetchWholeCatalog(params)
      .then(items => {
        if (ignore) return;
        setMovies(items);
        setLoadError(false);
        setLoadedKey(requestKey);
      })
      .catch(error => {
        if (ignore) return;
        console.warn('Каталог недоступний:', error);
        setMovies([]);
        setLoadError(true);
        setLoadedKey(requestKey);
      });
    return () => {
      ignore = true;
    };
  }, [selectedCategory, filterGenre, filterYear, sortKey, requestKey]);

  const filteredMovies = movies.filter(movie => {
    if (selectedCategory) {
      const cat = (movie.category || '').toLowerCase();
      const sel = selectedCategory.toLowerCase();
      const isMovie = (sel === 'фільми' || sel === 'movie' || sel === 'movies') && 
                      (cat === 'фільми' || cat === 'movie' || cat === 'movies');
      const isSeries = (sel === 'серіали' || sel === 'series' || sel === 'tv shows') && 
                       (cat === 'серіали' || cat === 'series' || cat === 'tv shows');
      const isCartoons = (sel === 'мультфільми' || sel === 'cartoons') && cat === 'cartoons';
      if (!isMovie && !isSeries && !isCartoons && cat !== sel) {
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

  // Sorting is applied only to the filtered selection (FR-010)
  const displayedMovies = sortMovies(filteredMovies, sortKey);

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
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
          <span className="hidden sm:inline">{isUkr ? 'Сортувати:' : 'Sort by:'}</span>
          <select
            aria-label={isUkr ? 'Сортування' : 'Sorting'}
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value)}
            className="px-3 py-1.5 border rounded-lg bg-white dark:bg-gray-800 dark:border-gray-700 dark:text-white text-sm"
          >
            {SORT_OPTIONS.map(option => (
              <option key={option.key || 'default'} value={option.key}>
                {isUkr ? option.labelUkr : option.labelEn}
              </option>
            ))}
          </select>
        </label>
      </div>
      
      {loading ? (
        <div className="py-12 text-center text-gray-500 text-sm">{isUkr ? 'Завантаження...' : 'Loading...'}</div>
      ) : loadError ? (
        <div role="alert" className="py-12 text-center text-sm text-red-600 dark:text-red-400">
          {isUkr ? 'Каталог тимчасово недоступний: сервер не відповідає. Спробуйте оновити сторінку.' : 'The catalog is unavailable: the server is not responding. Please reload the page.'}
        </div>
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

      {!loading && !loadError && displayedMovies.length > 0 && (
        <p className="mt-8 text-center text-xs text-gray-500 dark:text-gray-400">
          {isUkr ? `Усього: ${displayedMovies.length}` : `Total: ${displayedMovies.length}`}
        </p>
      )}
    </section>
  );
}