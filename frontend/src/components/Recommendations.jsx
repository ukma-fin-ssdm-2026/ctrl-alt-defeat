import { useEffect, useState } from 'react';
import apiClient from '../api/client';
import { CURRENT_USER_ID } from '../auth/currentUser';
import MovieCard from './MovieCard';

const RECOMMENDATIONS_LIMIT = 10;

// "Recommended for you" block on the home page (FR-007)
export default function Recommendations({
  user,
  isLoggedIn,
  openAuth,
  onSelectMovie,
  language = 'UKR',
  watchlist = [],
  onToggleWatchlist,
}) {
  const isUkr = language === 'UKR';
  const [result, setResult] = useState(null); // { userId, data } or { userId, error }
  const activeUserId = user?.user_id || CURRENT_USER_ID;

  useEffect(() => {
    if (!isLoggedIn) return undefined;

    // Ignore the response if the user logged out while the request was in flight
    let ignore = false;
    apiClient.get('/recommendations', { params: { user_id: activeUserId, limit: RECOMMENDATIONS_LIMIT } })
      .then(response => {
        if (!ignore) setResult({ userId: activeUserId, data: response.data });
      })
      .catch(error => {
        console.warn('Recommendations are unavailable:', error);
        if (!ignore) setResult({ userId: activeUserId, error: true });
      });
    return () => {
      ignore = true;
    };
  }, [isLoggedIn, activeUserId]);

  const heading = (
    <h2 className="text-xl font-black text-gray-900 dark:text-white border-l-4 border-yellow-500 pl-3">
      {isUkr ? 'Рекомендовано для вас' : 'Recommended for you'}
    </h2>
  );

  if (!isLoggedIn) {
    return (
      <section className="py-6" aria-label={isUkr ? 'Рекомендації' : 'Recommendations'}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-yellow-50 dark:bg-gray-800 border border-yellow-200 dark:border-gray-700 rounded-2xl p-5">
          <div>
            {heading}
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-2 pl-4">
              {isUkr
                ? 'Увійдіть і оцініть кілька фільмів, щоб отримати персональні рекомендації.'
                : 'Log in and rate a few titles to get personal recommendations.'}
            </p>
          </div>
          <button
            onClick={openAuth}
            className="self-start sm:self-center px-5 py-2 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold rounded-lg text-sm transition-colors shadow"
          >
            {isUkr ? 'Увійти' : 'Log in'}
          </button>
        </div>
      </section>
    );
  }

  const isLoaded = result && result.userId === CURRENT_USER_ID;
  // Hide the block if the backend is unavailable or has nothing to recommend
  if (isLoaded && (result.error || result.data.items.length === 0)) return null;

  const data = isLoaded ? result.data : null;

  return (
    <section className="py-6" aria-label={isUkr ? 'Рекомендації' : 'Recommendations'}>
      <div className="mb-4">
        {heading}
        {data && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 pl-4">
            {data.personalized
              ? `${isUkr ? 'На основі ваших улюблених жанрів' : 'Based on your favorite genres'}: ${data.favorite_genres.join(', ')}`
              : (isUkr
                ? 'Найкраще з каталогу. Оцініть кілька фільмів, і ми підберемо рекомендації саме для вас.'
                : 'Top rated picks. Rate a few titles and we will tailor recommendations for you.')}
          </p>
        )}
      </div>

      {!data ? (
        <div className="py-8 text-center text-gray-500 text-sm">{isUkr ? 'Підбираємо рекомендації...' : 'Loading recommendations...'}</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
          {data.items.map(movie => (
            <MovieCard
              key={movie.content_id || movie.id}
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
