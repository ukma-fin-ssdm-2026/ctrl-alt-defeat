import { translateGenre } from '../utils/genres';
import { posterFor } from '../utils/poster';

export default function MovieCard({ movie, onSelect, language = 'UKR', isWatchlisted, onToggleWatchlist }) {
  const isUkr = language === 'UKR';

  const primaryTitle = isUkr ? movie.title : (movie.title_en || movie.titleEn || movie.title);
  const secondaryTitle = isUkr ? (movie.title_en || movie.titleEn || '') : movie.title;

  const getCategoryLabel = (cat) => {
    if (!cat) return '';
    const c = cat.toLowerCase();
    if (c === 'фільми' || c === 'movie' || c === 'movies') return isUkr ? 'Фільми' : 'Movies';
    if (c === 'серіали' || c === 'series' || c === 'tv shows') return isUkr ? 'Серіали' : 'TV Shows';
    if (c === 'мультфільми' || c === 'cartoons') return isUkr ? 'Мультфільми' : 'Cartoons';
    return cat;
  };

  const getGenreLabel = (genre) => translateGenre(genre, isUkr ? 'UKR' : 'EN');

  return (
    <div
      className="group bg-white dark:bg-gray-800 rounded-xl overflow-hidden border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-md transition-all flex flex-col relative"
    >
      <button
        type="button"
        onClick={() => onSelect(movie)}
        className="w-full flex flex-col flex-1 text-left cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-yellow-500"
      >
        <div className="relative aspect-[2/3] overflow-hidden bg-gray-100 dark:bg-gray-700 w-full">
          <img
            src={posterFor(movie, language)}
            alt={primaryTitle}
            // Hundreds of posters on one page: load only those near the screen
            loading="lazy"
            decoding="async"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />

          {movie.category && (
            <span className="absolute top-2 left-2 px-2 py-0.5 bg-black/60 backdrop-blur-md text-white font-bold text-[10px] rounded-md uppercase tracking-wider">
              {getCategoryLabel(movie.category)}
            </span>
          )}

          <div className="absolute bottom-2 right-2 px-2 py-1 bg-yellow-500 text-gray-900 font-black text-xs rounded-lg shadow">
            ★ {movie.rating}
          </div>
        </div>

        <div className="p-3 flex flex-col flex-1 justify-between w-full">
          <div>
            <h3 className="font-bold text-sm text-gray-900 dark:text-white line-clamp-1 group-hover:text-yellow-600 dark:group-hover:text-yellow-400 transition-colors">
              {primaryTitle}
            </h3>

            {secondaryTitle && secondaryTitle !== primaryTitle && (
              <p className="text-[10px] text-gray-400 dark:text-gray-500 line-clamp-1 mt-0.5">
                {secondaryTitle}
              </p>
            )}
          </div>

          <p className="text-xs text-gray-400 mt-2">
            {movie.year} • {getGenreLabel(movie.genre)}
          </p>
        </div>
      </button>

      {onToggleWatchlist && (
        <button
          type="button"
          onClick={() => {
            onToggleWatchlist(movie.id || movie.content_id);
          }}
          className={`absolute top-2 right-2 z-20 p-2 rounded-full shadow-md transition-all ${
            isWatchlisted
              ? 'bg-yellow-500 text-gray-900 opacity-100'
              : 'bg-black/60 text-white opacity-0 group-hover:opacity-100 hover:bg-yellow-500 hover:text-gray-900'
          }`}
          title={isWatchlisted
            ? (isUkr ? 'Видалити зі списку' : 'Remove from watchlist')
            : (isUkr ? 'Додати до списку' : 'Add to watchlist')}
          aria-label={isWatchlisted
            ? (isUkr ? 'Видалити зі списку' : 'Remove from watchlist')
            : (isUkr ? 'Додати до списку' : 'Add to watchlist')}
        >
          {isWatchlisted ? '✓' : '+'}
        </button>
      )}
    </div>
  );
}