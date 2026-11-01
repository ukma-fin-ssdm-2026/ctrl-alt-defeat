import { useState, useEffect } from 'react';
import apiClient from '../api/client';

// TODO: replace with the real user id once authentication is implemented
const CURRENT_USER_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
const MIN_TEXT = 10;
const MAX_TEXT = 5000;

function ReviewContent({ text, isSpoiler, language = 'UKR' }) {
  const [revealed, setRevealed] = useState(false);
  const isUkr = language === 'UKR';

  // Rating-only review: nothing to render
  if (!text) return null;

  if (!isSpoiler) {
    return <p className="text-sm text-gray-700 dark:text-gray-300 mt-2">{text}</p>;
  }

  return (
    <div className="mt-2">
      {!revealed ? (
        <div className="bg-yellow-50 dark:bg-gray-700/40 border border-yellow-200 dark:border-gray-600 p-3 rounded-xl flex items-center justify-between">
          <span className="text-xs font-semibold text-yellow-700 dark:text-yellow-400">
            {isUkr ? '⚠️ Цей відгук містить спойлер' : '⚠️ This review contains a spoiler'}
          </span>
          <button 
            onClick={() => setRevealed(true)}
            className="px-3 py-1 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold text-xs rounded-lg transition-colors shadow-sm"
          >
            {isUkr ? 'Показати спойлер' : 'Show Spoiler'}
          </button>
        </div>
      ) : (
        <div className="bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 p-3 rounded-xl">
          <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">{text}</p>
          <button 
            onClick={() => setRevealed(false)}
            className="text-xs text-yellow-600 dark:text-yellow-400 font-semibold hover:underline"
          >
            {isUkr ? 'Приховати спойлер' : 'Hide Spoiler'}
          </button>
        </div>
      )}
    </div>
  );
}

export default function MovieDetails({ 
  movie, 
  isLoggedIn, 
  openAuth, 
  onBack, 
  language = 'UKR', 
  isWatchlisted = false, 
  onToggleWatchlist 
}) {
  const [rating, setRating] = useState(10);
  const [reviewText, setReviewText] = useState('');
  const [isSpoiler, setIsSpoiler] = useState(false);
  const [reviews, setReviews] = useState([]);
  // Loading is derived: reviews are loading until they are fetched for the current movie
  const reviewsKey = movie.content_id || movie.id;
  const [loadedReviewsKey, setLoadedReviewsKey] = useState(null);
  const loadingReviews = loadedReviewsKey !== reviewsKey;

  const [formError, setFormError] = useState('');
  const isUkr = language === 'UKR';

  // Reviews may be loaded without a content filter, so match both user and movie
  const myReview = reviews.find(
    r => r.user_id === CURRENT_USER_ID && movie.content_id && r.content_id === movie.content_id
  );
  const trimmedLength = reviewText.trim().length;
  const textTooShort = trimmedLength > 0 && trimmedLength < MIN_TEXT;

  const primaryTitle = isUkr ? movie.title : (movie.title_en || movie.titleEn || movie.title);
  const secondaryTitle = isUkr ? (movie.title_en || movie.titleEn || 'Original Title') : movie.title;

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

  useEffect(() => {
    const contentUuid = movie.content_id;
    const params = contentUuid ? { content_id: contentUuid } : {};

    apiClient.get('/reviews', { params })
      .then(response => {
        const reviewList = response.data.items ? response.data.items : response.data;
        setReviews(reviewList.length > 0 ? reviewList : (movie.reviews || []));
        setLoadedReviewsKey(reviewsKey);
      })
      .catch(error => {
        console.warn("Бекенд рецензій недоступний, використовуємо приклади:", error);
        setReviews(movie.reviews || []);
        setLoadedReviewsKey(reviewsKey);
      });
  }, [movie, reviewsKey]);

  const handleSubmitReview = (e) => {
    e.preventDefault();
    setFormError('');
    const text = reviewText.trim();

    if (text && text.length < MIN_TEXT) {
      setFormError(isUkr
        ? `Текст має містити щонайменше ${MIN_TEXT} символів, або залиште поле порожнім, щоб поставити лише оцінку.`
        : `Text must be at least ${MIN_TEXT} characters, or leave it empty to submit a rating only.`);
      return;
    }
    if (text.length > MAX_TEXT) {
      setFormError(isUkr ? `Максимум ${MAX_TEXT} символів.` : `Maximum ${MAX_TEXT} characters.`);
      return;
    }

    const contentUuid = movie.content_id || "11111111-1111-1111-1111-111111111111";

    apiClient.post('/reviews', {
      user_id: CURRENT_USER_ID,
      content_id: contentUuid,
      rating: Number(rating),
      review_text: text || null,
      contains_spoilers: text ? isSpoiler : false,
    })
      .then(response => {
        setReviews([response.data, ...reviews]);
        setReviewText('');
        setIsSpoiler(false);
        setRating(10);
      })
      .catch(error => {
        if (error.response?.status === 409) {
          setFormError(isUkr ? 'Ви вже залишили рецензію на цей фільм.' : 'You have already reviewed this movie.');
        } else {
          setFormError(error.response?.data?.error?.message
            || (isUkr ? 'Не вдалося опублікувати рецензію.' : 'Failed to publish review.'));
        }
      });
  };

  const handleLike = (id) => {
    if (!isLoggedIn) {
      openAuth();
      return;
    }
    setReviews(reviews.map(rev => (rev.review_id === id || rev.id === id) ? { ...rev, likes: (rev.likes || 0) + 1 } : rev));
  };

  return (
    <div className="py-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <button 
          onClick={onBack}
          className="flex items-center gap-2 text-sm font-semibold text-yellow-600 dark:text-yellow-400 hover:underline"
        >
          {isUkr ? '← Назад до списку' : '← Back to list'}
        </button>

        {onToggleWatchlist && (
          <button
            onClick={() => onToggleWatchlist(movie.id || movie.content_id)}
            className={`px-4 py-2 rounded-xl font-bold text-sm transition-all shadow-sm flex items-center gap-2 ${
              isWatchlisted 
                ? 'bg-yellow-500 text-gray-900' 
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-yellow-500 hover:text-gray-900'
            }`}
          >
            {isWatchlisted ? (isUkr ? '✓ У списку перегляду' : '✓ In Watchlist') : (isUkr ? '+ Додати до списку' : '+ Add to Watchlist')}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12 bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
        <div>
          <img src={movie.img} alt={primaryTitle} className="w-full rounded-xl shadow-md object-cover aspect-[2/3]" />
        </div>
        <div className="md:col-span-2 flex flex-col justify-between">
          <div>
            <h1 className="text-3xl font-black text-gray-900 dark:text-white mb-1">{primaryTitle}</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{secondaryTitle}</p>
            
            {/* Опис з підтримкою мови */}
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-6 leading-relaxed">
              {isUkr 
                ? (movie.description || 'Опис цього фільму поки що відсутній.') 
                : (movie.description_en || movie.descriptionEn || movie.description || 'No description available.')}
            </p>

            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3 text-sm mb-6">
              <div>
                <dt className="text-gray-500 dark:text-gray-400 font-semibold">{isUkr ? 'Рік:' : 'Year:'}</dt>
                <dd className="text-gray-900 dark:text-gray-200 font-medium">{movie.year}</dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-gray-400 font-semibold">{isUkr ? 'Жанр:' : 'Genre:'}</dt>
                <dd className="text-gray-900 dark:text-gray-200 font-medium">{getGenreLabel(movie.genre)}</dd>
              </div>
              <div><dt className="text-gray-500 dark:text-gray-400 font-semibold">IMDb:</dt><dd className="text-yellow-600 font-bold">★ {movie.rating} / 10</dd></div>
              {movie.runtime ? (
                <div>
                  <dt className="text-gray-500 dark:text-gray-400 font-semibold">{isUkr ? 'Тривалість:' : 'Runtime:'}</dt>
                  <dd className="text-gray-900 dark:text-gray-200 font-medium">
                    {movie.runtime} {isUkr ? 'хв' : 'min'}
                    {(movie.category || '').toLowerCase() === 'series' && (isUkr ? ' (серія)' : ' (episode)')}
                  </dd>
                </div>
              ) : null}
              <div><dt className="text-gray-500 dark:text-gray-400 font-semibold">Rotten Eggs:</dt><dd className="text-green-600 font-bold">🥚 {movie.rotten_rating || movie.rottenRating || '88%'}</dd></div>
            </dl>
          </div>
        </div>
      </div>

      <section className="mb-12 bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
        <h3 className="text-lg font-bold mb-4 text-gray-900 dark:text-white border-l-4 border-yellow-500 pl-3">
          {isUkr ? 'Залишити рецензію' : 'Leave a Review'}
        </h3>

        {!isLoggedIn ? (
          <div className="bg-yellow-50 dark:bg-gray-700/50 border border-yellow-200 dark:border-gray-600 rounded-xl p-4 text-center">
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
              {isUkr ? 'Щоб залишити відгук та поставити оцінку, увійдіть до акаунту.' : 'Please log in to leave a review and rating.'}
            </p>
            <button onClick={openAuth} className="px-5 py-2 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold rounded-lg text-sm transition-colors shadow">
              {isUkr ? 'Увійти / Зареєструватися' : 'Login / Register'}
            </button>
          </div>
        ) : myReview ? (
          <div className="bg-green-50 dark:bg-gray-700/50 border border-green-200 dark:border-gray-600 rounded-xl p-4 text-sm text-gray-700 dark:text-gray-300">
            {isUkr ? 'Ви вже оцінили цей фільм: ' : 'You have already rated this movie: '}
            <b>★ {myReview.rating}/10</b>
          </div>
        ) : (
          <form onSubmit={handleSubmitReview} className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                {isUkr ? 'Ваша оцінка:' : 'Your Rating:'}
              </label>
              <select 
                value={rating} 
                onChange={(e) => setRating(e.target.value)}
                className="px-3 py-1.5 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white text-sm font-bold"
              >
                {[10, 9, 8, 7, 6, 5, 4, 3, 2, 1].map(num => (
                  <option key={num} value={num}>{num} / 10</option>
                ))}
              </select>
            </div>

            <textarea 
              rows="4"
              value={reviewText}
              maxLength={MAX_TEXT}
              onChange={(e) => setReviewText(e.target.value)}
              placeholder={isUkr ? "Ваші враження від перегляду (необов'язково)..." : "Your thoughts about the movie (optional)..."}
              className={`w-full p-3 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:outline-none focus:ring-2 text-sm ${textTooShort ? 'border-red-400 focus:ring-red-400' : 'focus:ring-yellow-500'}`}
            />
            <div className={`flex justify-between text-xs -mt-2 ${textTooShort ? 'text-red-500' : 'text-gray-400'}`}>
              <span>{isUkr ? `Необов'язково. Від ${MIN_TEXT} до ${MAX_TEXT} символів` : `Optional. ${MIN_TEXT} to ${MAX_TEXT} characters`}</span>
              <span>{trimmedLength} / {MAX_TEXT}</span>
            </div>

            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" checked={isSpoiler} disabled={trimmedLength === 0} onChange={(e) => setIsSpoiler(e.target.checked)} className="w-4 h-4 text-yellow-500 rounded border-gray-300" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {isUkr ? 'Містить спойлер' : 'Contains spoiler'}
              </span>
            </label>

            {formError && (
              <div className="p-3 rounded-xl bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-300 text-sm">{formError}</div>
            )}

            <button type="submit" disabled={textTooShort} className="self-end px-6 py-2.5 bg-yellow-500 hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900 font-bold rounded-xl text-sm transition-colors shadow">
              {trimmedLength > 0
                ? (isUkr ? 'Опублікувати відгук' : 'Publish Review')
                : (isUkr ? 'Поставити оцінку' : 'Submit Rating')}
            </button>
          </form>
        )}
      </section>

      <section className="space-y-4">
        <h3 className="text-lg font-bold mb-4 text-gray-900 dark:text-white">
          {isUkr ? `Рецензії глядачів (${reviews.length})` : `Audience Reviews (${reviews.length})`}
        </h3>

        {loadingReviews ? (
          <p className="text-gray-500 text-sm">{isUkr ? 'Завантаження рецензій...' : 'Loading reviews...'}</p>
        ) : reviews.length === 0 ? (
          <p className="text-gray-500 text-sm">
            {isUkr ? 'Ще немає жодної рецензії. Будьте першим!' : 'No reviews yet. Be the first!'}
          </p>
        ) : (
          reviews.map((rev) => {
            const reviewId = rev.review_id || rev.id;
            return (
              <div key={reviewId} className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-100 dark:border-gray-700">
                <div className="flex items-start gap-3">
                  <img src={rev.avatar || 'https://picsum.photos/50?random=99'} alt="avatar" className="w-10 h-10 rounded-full object-cover" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <h4 className="font-bold text-sm text-gray-900 dark:text-white">{rev.author || (isUkr ? 'Глядач' : 'Viewer')}</h4>
                        <span className="px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300 font-bold text-xs rounded">
                          ★ {rev.rating}/10
                        </span>
                      </div>
                      <span className="text-xs text-gray-400">{rev.created_at ? new Date(rev.created_at).toLocaleDateString() : (isUkr ? 'щойно' : 'just now')}</span>
                    </div>
                    
                    <ReviewContent text={rev.review_text} isSpoiler={rev.contains_spoilers} language={language} />
                    
                    <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                      <button 
                        onClick={() => handleLike(reviewId)} 
                        className="hover:text-green-500 flex items-center gap-1 font-semibold transition-colors"
                      >
                        👍 {isUkr ? 'Підтримую' : 'Support'} ({rev.likes || 0}) {!isLoggedIn && <span className="text-[10px] text-gray-400">({isUkr ? 'потрібен вхід' : 'login required'})</span>}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </section>
    </div>
  );
}