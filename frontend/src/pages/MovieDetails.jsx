import { useState, useEffect } from 'react';
import apiClient from '../api/client';

function ReviewContent({ text, isSpoiler }) {
  const [revealed, setRevealed] = useState(false);

  if (!isSpoiler) {
    return <p className="text-sm text-gray-700 dark:text-gray-300 mt-2">{text}</p>;
  }

  return (
    <div className="mt-2">
      {!revealed ? (
        <div className="bg-yellow-50 dark:bg-gray-700/40 border border-yellow-200 dark:border-gray-600 p-3 rounded-xl flex items-center justify-between">
          <span className="text-xs font-semibold text-yellow-700 dark:text-yellow-400">⚠️ Цей відгук містить спойлер</span>
          <button 
            onClick={() => setRevealed(true)}
            className="px-3 py-1 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold text-xs rounded-lg transition-colors shadow-sm"
          >
            Показати спойлер
          </button>
        </div>
      ) : (
        <div className="bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 p-3 rounded-xl">
          <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">{text}</p>
          <button 
            onClick={() => setRevealed(false)}
            className="text-xs text-yellow-600 dark:text-yellow-400 font-semibold hover:underline"
          >
            Приховати спойлер
          </button>
        </div>
      )}
    </div>
  );
}

export default function MovieDetails({ movie, isLoggedIn, openAuth, onBack }) {
  const [rating, setRating] = useState(10);
  const [reviewText, setReviewText] = useState('');
  const [isSpoiler, setIsSpoiler] = useState(false);
  const [reviews, setReviews] = useState([]);
  const [loadingReviews, setLoadingReviews] = useState(true);

  useEffect(() => {
    setLoadingReviews(true);
    apiClient.get('/api/v1/reviews', {
      params: { content_id: movie.id }
    })
      .then(response => {
        const reviewList = response.data.items ? response.data.items : response.data;
        setReviews(reviewList.length > 0 ? reviewList : (movie.reviews || []));
        setLoadingReviews(false);
      })
      .catch(error => {
        console.warn("Бекенд рецензій недоступний, використовуємо приклади:", error);
        setReviews(movie.reviews || []);
        setLoadingReviews(false);
      });
  }, [movie.id]);

  const handleSubmitReview = (e) => {
    e.preventDefault();
    if (!reviewText.trim()) return;

    apiClient.post('/api/v1/reviews', {
      user_id: "3fa85f64-5717-4562-b3fc-2c963f66afa6", 
      content_id: movie.id,
      rating: Number(rating),
      review_text: reviewText,
      contains_spoilers: isSpoiler
    })
    .then(response => {
      setReviews([response.data, ...reviews]);
      setReviewText('');
      setIsSpoiler(false);
    })
    .catch(error => {
      console.error("Помилка публікації рецензії:", error);
      alert('Не вдалося опублікувати рецензію. Перевірте поля або політику вмісту.');
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
      <button 
        onClick={onBack}
        className="mb-6 flex items-center gap-2 text-sm font-semibold text-yellow-600 dark:text-yellow-400 hover:underline"
      >
        ← Назад до списку
      </button>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12 bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
        <div>
          <img src={movie.img} alt={movie.title} className="w-full rounded-xl shadow-md object-cover aspect-[2/3]" />
        </div>
        <div className="md:col-span-2 flex flex-col justify-between">
          <div>
            <h1 className="text-3xl font-black text-gray-900 dark:text-white mb-1">{movie.title}</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{movie.titleEn || 'Original Title'}</p>
            
            {/* 2. ВИВІД ОПИСУ ФІЛЬМУ */}
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-6 leading-relaxed">
              {movie.description || 'Опис цього фільму поки що відсутній.'}
            </p>

            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3 text-sm mb-6">
              <div><dt className="text-gray-500 dark:text-gray-400 font-semibold">Рік:</dt><dd className="text-gray-900 dark:text-gray-200 font-medium">{movie.year}</dd></div>
              <div><dt className="text-gray-500 dark:text-gray-400 font-semibold">Жанр:</dt><dd className="text-gray-900 dark:text-gray-200 font-medium">{movie.genre}</dd></div>
              <div><dt className="text-gray-500 dark:text-gray-400 font-semibold">IMDb:</dt><dd className="text-yellow-600 font-bold">★ {movie.rating} / 10</dd></div>
              <div><dt className="text-gray-500 dark:text-gray-400 font-semibold">Rotten Eggs:</dt><dd className="text-green-600 font-bold">🥚 {movie.rottenRating || '88%'}</dd></div>
            </dl>
          </div>
        </div>
      </div>

      <section className="mb-12 bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
        <h3 className="text-lg font-bold mb-4 text-gray-900 dark:text-white border-l-4 border-yellow-500 pl-3">
          Залишити рецензію
        </h3>

        {!isLoggedIn ? (
          <div className="bg-yellow-50 dark:bg-gray-700/50 border border-yellow-200 dark:border-gray-600 rounded-xl p-4 text-center">
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">Щоб залишити відгук та поставити оцінку, увійдіть до акаунту.</p>
            <button onClick={openAuth} className="px-5 py-2 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold rounded-lg text-sm transition-colors shadow">
              Увійти / Зареєструватися
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmitReview} className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Ваша оцінка:</label>
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
              onChange={(e) => setReviewText(e.target.value)}
              placeholder="Напишіть ваші враження від перегляду..."
              className="w-full p-3 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:outline-none focus:ring-2 focus:ring-yellow-500 text-sm"
            />

            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" checked={isSpoiler} onChange={(e) => setIsSpoiler(e.target.checked)} className="w-4 h-4 text-yellow-500 rounded border-gray-300" />
              <span className="text-sm text-gray-700 dark:text-gray-300">Містить спойлер</span>
            </label>

            <button type="submit" className="self-end px-6 py-2.5 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold rounded-xl text-sm transition-colors shadow">
              Опублікувати відгук
            </button>
          </form>
        )}
      </section>

      <section className="space-y-4">
        <h3 className="text-lg font-bold mb-4 text-gray-900 dark:text-white">Рецензії глядачів ({reviews.length})</h3>

        {loadingReviews ? (
          <p className="text-gray-500 text-sm">Завантаження рецензій...</p>
        ) : reviews.length === 0 ? (
          <p className="text-gray-500 text-sm">Ще немає жодної рецензії. Будьте першим!</p>
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
                        <h4 className="font-bold text-sm text-gray-900 dark:text-white">{rev.author || 'Глядач'}</h4>
                        <span className="px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300 font-bold text-xs rounded">
                          ★ {rev.rating}/10
                        </span>
                      </div>
                      <span className="text-xs text-gray-400">{rev.created_at ? new Date(rev.created_at).toLocaleDateString() : 'щойно'}</span>
                    </div>
                    
                    <ReviewContent text={rev.review_text} isSpoiler={rev.contains_spoilers} />
                    
                    <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                      <button 
                        onClick={() => handleLike(reviewId)} 
                        className="hover:text-green-500 flex items-center gap-1 font-semibold transition-colors"
                      >
                        👍 Підтримую ({rev.likes || 0}) {!isLoggedIn && <span className="text-[10px] text-gray-400">(потрібен вхід)</span>}
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