import { useState, useEffect } from 'react';
import apiClient from '../api/client';
import MovieCard from '../components/MovieCard';

export default function Home({ selectedCategory, selectedGenre, onSelectMovie }) {
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterGenre, setFilterGenre] = useState(selectedGenre || '');
  const [filterYear, setFilterYear] = useState('');

  // 6 examples
 const mockMovies = [
    { 
      id: 1, 
      title: 'Спасенний', 
      titleEn: 'Saved', 
      category: 'Фільми', 
      genre: 'Драма', 
      year: 2026, 
      rating: '8.4', 
      rottenRating: '88%', 
      img: 'https://picsum.photos/300/450?random=1',
      description: 'Драматична історія про виживання та моральний вибір у критичних умовах майбутнього, де кожен крок може стати останнім.',
      reviews: [
        { id: 101, author: 'Кінокритик UA', rating: 9, review_text: 'Неймовірна атмосфера та глибокий психологічний підтекст. Рекомендую до перегляду.', contains_spoilers: false, likes: 12, created_at: '2026-10-28T12:00:00Z' },
        { id: 102, author: 'SpoilerKing', rating: 8, review_text: 'Фільм чудовий, але майте на увазі: головний герой наприкінці все ж вирішує залишитися на станції сам.', contains_spoilers: true, likes: 5, created_at: '2026-10-29T15:30:00Z' }
      ]
    },
    { 
      id: 2, 
      title: 'Мама, я вагітна від прибульця', 
      titleEn: 'Alien Pregnancy', 
      category: 'Фільми', 
      genre: 'Комедія', 
      year: 2026, 
      rating: '6.9', 
      rottenRating: '70%', 
      img: 'https://picsum.photos/300/450?random=2',
      description: 'Безумна науково-фантастична комедія про звичайну родину з провінції, чиє життя перевертається з ніг на голову після неочікуваного візиту з космосу.',
      reviews: [
        { id: 201, author: 'Сміхомайстер', rating: 7, review_text: 'Сміявся з першої до останньої хвилини! Гумор специфічний, але працює.', contains_spoilers: false, likes: 8, created_at: '2026-10-27T18:10:00Z' },
        { id: 202, author: 'Галактичний експерт', rating: 6, review_text: 'Сюжет передбачуваний, а головний іншопланетянин виявляється сусідом дядьком Василем у костюмі.', contains_spoilers: true, likes: 3, created_at: '2026-10-29T20:00:00Z' }
      ]
    },
    { 
      id: 3, 
      title: 'Дивні Дива (Сезон 1)', 
      titleEn: 'Stranger Things', 
      category: 'Серіали', 
      genre: 'Фантастика', 
      year: 2016, 
      rating: '8.7', 
      rottenRating: '92%', 
      img: 'https://picsum.photos/300/450?random=5',
      description: 'Зникнення маленького хлопчика в містечку Гокінс розкриває таємницю секретних експериментів, надприродних сил та дивної дівчинки.',
      reviews: [
        { id: 301, author: 'RetroLover', rating: 10, review_text: 'Шедевр у стилі 80-х років. Саундтрек та акторська гра підлітків — на висоті.', contains_spoilers: false, likes: 25, created_at: '2026-10-20T10:00:00Z' },
        { id: 302, author: 'HawkinsPolice', rating: 9, review_text: 'Дуже круто, хоча вже на 7-й серії стає зрозуміло, що Одинадцята витратить усі сили й зникне у боротьбі з монстром.', contains_spoilers: true, likes: 14, created_at: '2026-10-22T11:15:00Z' }
      ]
    },
    { 
      id: 4, 
      title: 'Ужас з могили', 
      titleEn: 'Grave Horror', 
      category: 'Серіали', 
      genre: 'Жахи', 
      year: 2021, 
      rating: '7.2', 
      rottenRating: '65%', 
      img: 'https://picsum.photos/300/450?random=3',
      description: 'Антологія моторошних міських легенд, де кожен епізод занурює глядача в нову кошмарну історію з темного минулого.',
      reviews: [
        { id: 401, author: 'NightOwl', rating: 8, review_text: 'Локації та атмосфера тримають у напрузі весь епізод. Любителям жахів зайде.', contains_spoilers: false, likes: 6, created_at: '2026-10-25T23:00:00Z' },
        { id: 402, author: 'ScaryCat', rating: 6, review_text: 'У третій серії головний священник виявляється головним монстром, який усе це затіяв.', contains_spoilers: true, likes: 2, created_at: '2026-10-26T01:20:00Z' }
      ]
    },
    { 
      id: 5, 
      title: 'Шрек', 
      titleEn: 'Shrek', 
      category: 'Мультфільми', 
      genre: 'Комедія', 
      year: 2001, 
      rating: '7.9', 
      rottenRating: '90%', 
      img: 'https://picsum.photos/300/450?random=6',
      description: 'Воркливий огор на ім’я Шрек вирушає в подорож, щоб врятувати принцесу та повернути своє болото, але все йде зовсім не за планом.',
      reviews: [
        { id: 501, author: 'Оскар', rating: 10, review_text: 'Вічна класика анімації з чудовим гумором як для дітей, так і для дорослих.', contains_spoilers: false, likes: 30, created_at: '2026-10-15T14:00:00Z' },
        { id: 502, author: 'FionaFan', rating: 9, review_text: 'Неймовірний фінал, де принцеса назавжди залишається оґром і їй це подобається!', contains_spoilers: true, likes: 19, created_at: '2026-10-18T16:45:00Z' }
      ]
    },
    { 
      id: 6, 
      title: 'Джейн Доу проти Корнелла', 
      titleEn: 'Jane Doe vs Cornell', 
      category: 'Мультфільми', 
      genre: 'Документальний', 
      year: 2026, 
      rating: '9.0', 
      rottenRating: '95%', 
      img: 'https://picsum.photos/300/450?random=4',
      description: 'Глибоке документальне анімаційне розслідування однієї з найгучніших юридичних баталій у галузі технологій та авторського права.',
      reviews: [
        { id: 601, author: 'TechJurist', rating: 9, review_text: 'Дуже детально та цікаво подано складні юридичні речі через анімацію.', contains_spoilers: false, likes: 11, created_at: '2026-10-29T09:00:00Z' },
        { id: 602, author: 'CodeReviewer', rating: 9, review_text: 'У кінці суду зʼясовується, що ключовий доказ був сфальсифікований самим головним позивачем.', contains_spoilers: true, likes: 7, created_at: '2026-10-29T11:30:00Z' }
      ]
    },
  ];

  useEffect(() => {
    if (selectedGenre !== undefined) {
      setFilterGenre(selectedGenre);
    }
  }, [selectedGenre]);

  useEffect(() => {
    const params = {};
    if (selectedCategory) params.category = selectedCategory;
    if (filterGenre) params.genre = filterGenre;
    if (filterYear) params.year = filterYear;

    setLoading(true);
    apiClient.get('/api/movies', { params })
      .then(response => {
        const data = response.data.items || response.data;
        if (data && data.length > 0) {
          setMovies(data);
        } else {
          setMovies(mockMovies);
        }
        setLoading(false);
      })
      .catch(error => {
        console.warn("Бекенд фільмів ще недоступний, використовуємо локальні заглушки:", error);
        setMovies(mockMovies);
        setLoading(false);
      });
  }, [selectedCategory, filterGenre, filterYear]);

  const displayedMovies = movies.filter(movie => {
    if (selectedCategory && movie.category !== selectedCategory) return false;
    if (filterGenre && movie.genre !== filterGenre) return false;
    if (filterYear && movie.year !== Number(filterYear)) return false;
    return true;
  });

  const availableGenres = ['Бойовик', 'Комедія', 'Драма', 'Фантастика', 'Жахи', 'Документальний'];
  const availableYears = [2026, 2021, 2016, 2001];

  const titleText = filterGenre 
    ? `${selectedCategory || 'Категорія'} — Жанр: ${filterGenre}`
    : selectedCategory 
    ? `Всі ${selectedCategory.toLowerCase()}` 
    : 'Нещодавно додані';

  return (
    <section className="py-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 border-b border-gray-100 dark:border-gray-800 pb-4">
        <h2 className="text-xl font-black text-gray-900 dark:text-white border-l-4 border-yellow-500 pl-3">
          {titleText}
        </h2>

        <div className="flex flex-wrap items-center gap-3">
          <select 
            value={filterGenre} 
            onChange={(e) => setFilterGenre(e.target.value)}
            className="px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-xs font-semibold text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-yellow-500"
          >
            <option value="">Усі жанри</option>
            {availableGenres.map(g => <option key={g} value={g}>{g}</option>)}
          </select>

          <select 
            value={filterYear} 
            onChange={(e) => setFilterYear(e.target.value)}
            className="px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-xs font-semibold text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-yellow-500"
          >
            <option value="">Усі роки</option>
            {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
          </select>

          {(filterGenre || filterYear) && (
            <button 
              onClick={() => { setFilterGenre(''); setFilterYear(''); }}
              className="text-xs text-yellow-600 dark:text-yellow-400 font-bold hover:underline"
            >
              Скинути
            </button>
          )}
        </div>
      </div>
      
      {loading ? (
        <div className="py-12 text-center text-gray-500 text-sm">Завантаження...</div>
      ) : displayedMovies.length === 0 ? (
        <div className="py-12 text-center">
          <p className="text-gray-500 dark:text-gray-400 text-sm">Не знайдено жодного фільму за такими критеріями.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {displayedMovies.map(movie => (
            <MovieCard key={movie.id || movie.content_id} movie={movie} onSelect={onSelectMovie} />
          ))}
        </div>
      )}
    </section>
  );
}