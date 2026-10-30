import { useState, useRef, useEffect } from 'react';
const ALL_MOVIES = [
  { id: 1, title: 'Спасенний', titleEn: 'Saved', category: 'Фільми', genre: 'Драма', year: 2026, rating: '8.4', img: 'https://picsum.photos/300/450?random=1' },
  { id: 2, title: 'Мама, я вагітна від прибульця', titleEn: 'Mom, I am pregnant with an alien', category: 'Фільми', genre: 'Комедія', year: 2026, rating: '6.9', img: 'https://picsum.photos/300/450?random=2' },
  { id: 3, title: 'Ужас з могили', titleEn: 'Terror from Grave', category: 'Фільми', genre: 'Жахи', year: 1973, rating: '7.2', img: 'https://picsum.photos/300/450?random=3' },
  { id: 4, title: 'Джейн Доу проти Корнелла', titleEn: 'Jane Doe vs Cornell', category: 'Фільми', genre: 'Документальний', year: 2026, rating: '9.0', img: 'https://picsum.photos/300/450?random=4' },
  { id: 5, title: 'Дивні Дива (Сезон 1)', titleEn: 'Stranger Things', category: 'Серіали', genre: 'Фантастика', year: 2016, rating: '8.7', img: 'https://picsum.photos/300/450?random=5' },
  { id: 6, title: 'Шрек', titleEn: 'Shrek', category: 'Мультфільми', genre: 'Комедія', year: 2001, rating: '7.9', img: 'https://picsum.photos/300/450?random=6' },
];

export default function Header({ toggleTheme, isDarkMode, openAuth, onGoHome, onSelectCategory, onSelectGenre, onSelectMovie }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [isOpenSuggestions, setIsOpenSuggestions] = useState(false);
  const searchRef = useRef(null);

  const categories = [
    { name: 'Фільми', key: 'Фільми' },
    { name: 'Серіали', key: 'Серіали' },
    { name: 'Мультфільми', key: 'Мультфільми' }
  ];
  const genres = ['Бойовик', 'Комедія', 'Драма', 'Фантастика', 'Жахи', 'Трилер', 'Детектив', 'Документальний'];

  const suggestions = searchQuery.trim() === '' ? [] : ALL_MOVIES.filter(movie => 
    movie.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (movie.titleEn && movie.titleEn.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  useEffect(() => {
    function handleClickOutside(event) {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setIsOpenSuggestions(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="sticky top-0 z-40 bg-white dark:bg-gray-800 shadow-md transition-colors duration-300">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between gap-4">
        <div 
          onClick={onGoHome} 
          className="flex items-center gap-3 font-bold text-xl cursor-pointer"
        >
          <img src="/logo.png" alt="Rotten Eggs Logo" className="h-10 w-auto object-contain" />
          <span className="hidden sm:block text-gray-900 dark:text-white font-black tracking-wider">
            ROTTEN <span className="text-yellow-500">EGGS</span>
          </span>
        </div>

        {}
        <div className="flex-1 max-w-md relative" ref={searchRef}>
          <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setIsOpenSuggestions(true);
            }}
            onFocus={() => setIsOpenSuggestions(true)}
            placeholder="Пошук ..." 
            className="w-full px-4 py-2 rounded-full border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-yellow-500 transition-all text-sm"
          />

          {isOpenSuggestions && suggestions.length > 0 && (
            <div className="absolute left-0 right-0 top-full mt-2 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-100 dark:border-gray-700 overflow-hidden z-50">
              {suggestions.map(movie => (
                <div 
                  key={movie.id}
                  onClick={() => {
                    onSelectMovie(movie);
                    setSearchQuery('');
                    setIsOpenSuggestions(false);
                  }}
                  className="px-4 py-2.5 hover:bg-yellow-50 dark:hover:bg-gray-700/60 cursor-pointer flex items-center gap-3 transition-colors border-b border-gray-50 dark:border-gray-700/50 last:border-none"
                >
                  <img src={movie.img} alt={movie.title} className="w-8 h-10 object-cover rounded shadow-sm" />
                  <div className="flex-1 overflow-hidden">
                    <h4 className="text-xs font-bold text-gray-900 dark:text-white truncate">{movie.title}</h4>
                    <p className="text-[10px] text-gray-500 dark:text-gray-400 truncate">{movie.year} • {movie.genre}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={toggleTheme} 
            className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-xl transition-colors"
            title="Переключити тему"
          >
            {isDarkMode ? '☀️' : '🌙'}
          </button>
          <button 
            onClick={openAuth}
            className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold rounded-lg transition-colors text-sm whitespace-nowrap shadow-sm"
          >
            Увійти в профіль
          </button>
        </div>
      </div>

      <nav className="border-t border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50 hidden md:block">
        <div className="container mx-auto px-4 flex gap-8">
          {categories.map((cat) => (
            <div key={cat.key} className="relative group py-3">
              <button 
                onClick={() => onSelectCategory(cat.key)}
                className="flex items-center gap-1 font-semibold text-gray-700 dark:text-gray-200 hover:text-yellow-500 dark:hover:text-yellow-400 transition-colors text-sm"
              >
                {cat.name}
                <span className="text-xs transition-transform group-hover:rotate-180">▾</span>
              </button>
              
              <div className="absolute left-0 top-full hidden group-hover:block w-64 bg-white dark:bg-gray-800 shadow-xl rounded-b-xl border border-gray-100 dark:border-gray-700 p-4 z-50">
                <div className="grid grid-cols-2 gap-2">
                  {genres.map(genre => (
                    <button 
                      key={genre} 
                      onClick={() => onSelectGenre(cat.key, genre)} 
                      className="text-left px-2 py-1.5 hover:bg-yellow-50 dark:hover:bg-gray-700/50 text-gray-600 dark:text-gray-300 hover:text-yellow-600 dark:hover:text-yellow-400 rounded text-xs transition-colors"
                    >
                      {genre}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </nav>
    </header>
  );
}