export default function MovieCard({ movie, onSelect, language = 'UKR', isWatchlisted, onToggleWatchlist }) {
  const isUkr = language === 'UKR';
  
  const primaryTitle = isUkr ? movie.title : (movie.titleEn || movie.title);
  const secondaryTitle = isUkr ? (movie.titleEn || '') : movie.title;

  const getCategoryLabel = (cat) => {
    if (!cat) return '';
    if (cat === 'Фільми') return isUkr ? 'Фільми' : 'Movies';
    if (cat === 'Серіали') return isUkr ? 'Серіали' : 'TV Shows';
    if (cat === 'Мультфільми') return isUkr ? 'Мультфільми' : 'Cartoons';
    return cat;
  };

  const genreTranslations = {
    'Бойовик': 'Action',
    'Комедія': 'Comedy',
    'Драма': 'Drama',
    'Фантастика': 'Sci-Fi',
    'Жахи': 'Horror',
    'Трилер': 'Thriller',
    'Детектив': 'Detective',
    'Документальний': 'Documentary'
  };

  const getGenreLabel = (genre) => {
    if (!genre) return '';
    if (isUkr) return genre;
    return genreTranslations[genre] || genre;
  };

  return (
    <div 
      onClick={() => onSelect(movie)}
      className="group cursor-pointer bg-white dark:bg-gray-800 rounded-xl overflow-hidden border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-md transition-all flex flex-col relative"
    >
      {onToggleWatchlist && (
        <button 
          onClick={(e) => { 
            e.stopPropagation(); 
            onToggleWatchlist(movie.id || movie.content_id); 
          }}
          className={`absolute top-2 right-2 z-20 p-2 rounded-full shadow-md transition-all ${
            isWatchlisted 
              ? 'bg-yellow-500 text-gray-900 opacity-100' 
              : 'bg-black/60 text-white opacity-0 group-hover:opacity-100 hover:bg-yellow-500 hover:text-gray-900'
          }`}
          title={isWatchlisted ? (isUkr ? "Видалити зі списку" : "Remove from watchlist") : (isUkr ? "Додати до списку" : "Add to watchlist")}
        >
          {isWatchlisted ? '✓' : '+'}
        </button>
      )}

      <div className="relative aspect-[2/3] overflow-hidden bg-gray-100 dark:bg-gray-700">
        <img 
          src={movie.img} 
          alt={primaryTitle} 
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" 
        />
        
        {}
        {movie.category && (
          <span className="absolute top-2 left-2 px-2 py-0.5 bg-black/60 backdrop-blur-md text-white font-bold text-[10px] rounded-md uppercase tracking-wider">
            {getCategoryLabel(movie.category)}
          </span>
        )}

        <div className="absolute bottom-2 right-2 px-2 py-1 bg-yellow-500 text-gray-900 font-black text-xs rounded-lg shadow">
          ★ {movie.rating}
        </div>
      </div>
      
      <div className="p-3 flex flex-col flex-1 justify-between">
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
        
        {}
        <p className="text-xs text-gray-400 mt-2">
          {movie.year} • {getGenreLabel(movie.genre)}
        </p>
      </div>
    </div>
  );
}