import { useState, useRef, useEffect } from 'react';
import { mockMovies } from '../data/mockData';

export default function Header({ 
  toggleTheme, 
  isDarkMode, 
  openAuth, 
  onGoHome, 
  onSelectCategory, 
  onApplyFilter,
  onSelectMovie,
  user,
  onLogout,
  onGoProfile,
  language,
  onToggleLanguage
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [isOpenSuggestions, setIsOpenSuggestions] = useState(false);
  
  const [activeDropdown, setActiveDropdown] = useState(null);

  const [menuGenre, setMenuGenre] = useState('');
  const [menuYear, setMenuYear] = useState('');

  const searchRef = useRef(null);
  const isUkr = language === 'UKR';

  const categories = [
    { name: isUkr ? 'Фільми' : 'Movies', key: 'Фільми' },
    { name: isUkr ? 'Серіали' : 'TV Shows', key: 'Серіали' },
    { name: isUkr ? 'Мультфільми' : 'Cartoons', key: 'Мультфільми' }
  ];
  
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

  const genres = [
    'Бойовик', 'Комедія', 'Драма', 'Фантастика', 'Жахи', 
    'Трилер', 'Детектив', 'Документальний', 'Біографія', 
    'Історія', 'Мелодрама', 'Кримінал', 'Музика', 'Пригоди'
  ];

  const availableYears = [2026, 2024, 2023, 2021, 2020, 2019, 2017, 2016, 2014, 2011, 2010, 2008, 2001, 1994];

  const suggestions = searchQuery.trim() === '' ? [] : mockMovies.filter(movie => 
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

        <div className="flex-1 max-w-md relative" ref={searchRef}>
          <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setIsOpenSuggestions(true);
            }}
            onFocus={() => setIsOpenSuggestions(true)}
            placeholder={isUkr ? "Пошук ..." : "Search ..."} 
            className="w-full px-4 py-2 rounded-full border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-yellow-500 transition-all text-sm"
          />

          {isOpenSuggestions && suggestions.length > 0 && (
            <div className="absolute left-0 right-0 top-full mt-2 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-100 dark:border-gray-700 overflow-hidden z-50">
              {suggestions.map(movie => {
                const mainTitle = !isUkr ? (movie.titleEn || movie.title) : movie.title;
                const subTitle = !isUkr ? movie.title : movie.titleEn;

                return (
                  <div 
                    key={movie.id}
                    onClick={() => {
                      onSelectMovie(movie);
                      setSearchQuery('');
                      setIsOpenSuggestions(false);
                    }}
                    className="px-4 py-2.5 hover:bg-yellow-50 dark:hover:bg-gray-700/60 cursor-pointer flex items-center gap-3 transition-colors border-b border-gray-50 dark:border-gray-700/50 last:border-none"
                  >
                    <img src={movie.img} alt={mainTitle} className="w-8 h-10 object-cover rounded shadow-sm" />
                    <div className="flex-1 overflow-hidden">
                      <h4 className="text-xs font-bold text-gray-900 dark:text-white truncate">{mainTitle}</h4>
                      <p className="text-[10px] text-gray-500 dark:text-gray-400 truncate">
                        {subTitle ? `${subTitle} • ` : ''}{movie.year} • {getGenreLabel(movie.genre)}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={onToggleLanguage} 
            className="flex items-center font-bold text-xs bg-gray-100 dark:bg-gray-700 px-3 py-1.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 transition shadow-sm"
          >
            <span className={language === 'UKR' ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-400 dark:text-gray-500'}>UKR</span>
            <span className="text-gray-400 dark:text-gray-500 mx-1">/</span>
            <span className={language === 'EN' ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-400 dark:text-gray-500'}>EN</span>
          </button>

          <button 
            onClick={toggleTheme} 
            className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-xl transition-colors"
            title={isUkr ? 'Переключити тему' : 'Toggle theme'}
          >
            {isDarkMode ? '☀️' : '🌙'}
          </button>
          
          {user ? (
            <div className="flex items-center gap-2">
              <button 
                onClick={onGoProfile} 
                className="font-semibold text-gray-800 dark:text-gray-200 hover:text-yellow-500 transition text-sm hidden sm:block"
                title={isUkr ? 'Мій профіль' : 'My profile'}
              >
                {user.username}
              </button>
              <button 
                onClick={onLogout}
                className="px-3 py-1.5 bg-red-50 dark:bg-red-900/30 text-red-600 font-bold rounded-lg transition-colors text-xs shadow-sm hover:bg-red-100"
              >
                {isUkr ? 'Вийти' : 'Logout'}
              </button>
            </div>
          ) : (
            <button 
              onClick={openAuth}
              className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold rounded-lg transition-colors text-sm whitespace-nowrap shadow-sm"
            >
              {isUkr ? 'Увійти' : 'Login'}
            </button>
          )}
        </div>
      </div>

      {}
      <nav className="border-t border-gray-100 dark:border-gray-700 bg-gray-50/80 dark:bg-gray-800/80 backdrop-blur-md hidden md:block">
        <div className="container mx-auto px-4 flex gap-8 relative">
          {categories.map((cat) => {
            const isMenuOpen = activeDropdown === cat.key;

            return (
              <div 
                key={cat.key} 
                className="relative py-3"
                onMouseEnter={() => {
                  if (window.dropdownTimeout) clearTimeout(window.dropdownTimeout);
                  setActiveDropdown(cat.key);
                }}
                onMouseLeave={() => {
                  window.dropdownTimeout = setTimeout(() => {
                    setActiveDropdown(null);
                  }, 350);
                }}
              >
                <button 
                  onClick={() => {
                    setMenuGenre('');
                    setMenuYear('');
                    onSelectCategory(cat.key);
                    setActiveDropdown(null);
                  }}
                  className="flex items-center gap-1 font-bold text-gray-800 dark:text-gray-100 hover:text-yellow-500 dark:hover:text-yellow-400 transition-colors text-sm"
                >
                  {cat.name}
                  <span className={`text-xs transition-transform ${isMenuOpen ? 'rotate-180' : ''}`}>▾</span>
                </button>
                
                {isMenuOpen && (
                  <div className="absolute left-0 top-full w-[640px] bg-white dark:bg-gray-800 shadow-2xl rounded-2xl border border-gray-100 dark:border-gray-700 p-5 z-50">
                    
                    <div className="pb-4 mb-4 border-b border-gray-100 dark:border-gray-700 flex items-center gap-2">
                      <span className="text-xs font-black text-gray-400 uppercase tracking-wider whitespace-nowrap">
                        {isUkr ? 'Підбір:' : 'Filter:'}
                      </span>

                      <select 
                        value={menuGenre}
                        onChange={(e) => setMenuGenre(e.target.value)}
                        className="px-3 py-1.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-yellow-500 flex-1"
                      >
                        <option value="">{isUkr ? 'Будь-який жанр' : 'Any Genre'}</option>
                        {genres.map(g => (
                          <option key={g} value={g}>{getGenreLabel(g)}</option>
                        ))}
                      </select>

                      <select 
                        value={menuYear}
                        onChange={(e) => setMenuYear(e.target.value)}
                        className="px-3 py-1.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-yellow-500 w-32"
                      >
                        <option value="">{isUkr ? 'Усі роки' : 'All Years'}</option>
                        {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
                      </select>

                      <button 
                        onClick={() => {
                          if (onApplyFilter) {
                            onApplyFilter(cat.key, menuGenre, menuYear);
                          }
                          setActiveDropdown(null);
                        }}
                        className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-700 text-white font-bold rounded-xl text-xs transition-colors shadow-sm whitespace-nowrap"
                      >
                        {isUkr ? 'Погнали!' : 'Go!'}
                      </button>

                      {(menuGenre || menuYear) && (
                        <button 
                          onClick={() => {
                            setMenuGenre('');
                            setMenuYear('');
                            if (onApplyFilter) {
                              onApplyFilter(cat.key, '', '');
                            }
                          }}
                          className="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 text-gray-700 dark:text-gray-200 font-bold rounded-xl text-xs transition-colors shadow-sm whitespace-nowrap"
                        >
                          {isUkr ? 'Скинути' : 'Reset'}
                        </button>
                      )}
                    </div>

                    <div className="grid grid-cols-4 gap-2">
                      {genres.map(genre => (
                        <button 
                          key={genre} 
                          onClick={() => {
                            setMenuGenre(genre);
                            if (onApplyFilter) {
                              onApplyFilter(cat.key, genre, menuYear);
                            }
                            setActiveDropdown(null);
                          }} 
                          className="text-left px-3 py-1.5 hover:bg-yellow-50 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-200 hover:text-yellow-600 dark:hover:text-yellow-400 rounded-xl text-xs font-medium transition-colors truncate"
                        >
                          {getGenreLabel(genre)}
                        </button>
                      ))}
                    </div>

                  </div>
                )}
              </div>
            );
          })}
        </div>
      </nav>
    </header>
  );
}