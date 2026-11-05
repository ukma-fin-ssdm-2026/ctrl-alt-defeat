import { useState, useEffect } from 'react';
import apiClient from '../api/client';
import ReviewComments from '../components/ReviewComments';
import BanNotice from '../components/BanNotice';
import BanUserDialog from '../components/BanUserDialog';
import ReviewVotes from '../components/ReviewVotes';
import { applyVote, nextVote } from '../utils/reviewVotes';
import { isUuid } from '../utils/uuid';
import { formatAudienceRating } from '../utils/audienceRating';
import { translateGenre } from '../utils/genres';
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
  user,
  isLoggedIn, 
  openAuth, 
  onBack, 
  language = 'UKR', 
  isWatchlisted = false, 
  onToggleWatchlist,
  isWatched = false,
  onToggleWatched,
  onReviewsChanged
}) {
  const [rating, setRating] = useState(10);
  // FR-009: the review author the administrator is banning
  const [banTarget, setBanTarget] = useState(null);
  const [banDoneFor, setBanDoneFor] = useState(null);
  const [reviewText, setReviewText] = useState('');
  const [isSpoiler, setIsSpoiler] = useState(false);
  const [reviews, setReviews] = useState([]);
  // Loading is derived: reviews are loading until they are fetched for the current movie
  const reviewsKey = movie.content_id || movie.id;
  const [loadedReviewsKey, setLoadedReviewsKey] = useState(null);
  const loadingReviews = loadedReviewsKey !== reviewsKey;

  const [formError, setFormError] = useState('');
  const isUkr = language === 'UKR';

  const myReview = reviews.find(
    r => user?.user_id && r.user_id === user.user_id && movie.content_id && r.content_id === movie.content_id
  );
  // Only catalog titles stored on the backend can be reviewed
  const isCatalogTitle = isUuid(movie.content_id);
  const trimmedLength = reviewText.trim().length;
  const textTooShort = trimmedLength > 0 && trimmedLength < MIN_TEXT;

  const primaryTitle = isUkr ? movie.title : (movie.title_en || movie.titleEn || movie.title);
  const secondaryTitle = isUkr ? (movie.title_en || movie.titleEn || 'Original Title') : movie.title;


  const getGenreLabel = (genre) => translateGenre(genre, isUkr ? 'UKR' : 'EN');

  useEffect(() => {
    const contentUuid = movie.content_id;
    let ignore = false;

    // Without a catalog id there is nothing to filter by: never load the reviews of all movies
    const request = isUuid(contentUuid)
      ? apiClient.get('/reviews', { params: { content_id: contentUuid } })
      : Promise.resolve({ data: { items: [] } });

    request
      .then(response => {
        if (ignore) return;
        const reviewList = response.data.items ? response.data.items : response.data;
        // Defense in depth: keep only the reviews of this movie
        const ownReviews = reviewList.filter(r => r.content_id === contentUuid);
        setReviews(ownReviews.length > 0 ? ownReviews : (movie.reviews || []));
        setLoadedReviewsKey(reviewsKey);
      })
      .catch(error => {
        if (ignore) return;
        console.warn("Бекенд рецензій недоступний, використовуємо приклади:", error);
        setReviews(movie.reviews || []);
        setLoadedReviewsKey(reviewsKey);
      });
    // Ignore a late response for the previously opened movie
    return () => {
      ignore = true;
    };
  }, [movie, reviewsKey]);

  // My votes for the reviews of this movie, to highlight the chosen button
  const voterId = user?.user_id ?? null;
  const votesKey = `${movie.content_id}|${voterId}`;
  const [votesState, setVotesState] = useState({ key: null, votes: {} });
  const [voteError, setVoteError] = useState('');
  useEffect(() => {
    if (!voterId || !isUuid(movie.content_id)) return undefined;
    let ignore = false;
    apiClient.get('/reviews/votes/mine', { params: { content_id: movie.content_id } })
      .then(response => {
        if (ignore) return;
        const votes = Object.fromEntries((response.data.items || []).map(item => [item.review_id, item.value]));
        setVotesState({ key: votesKey, votes });
      })
      .catch(() => { if (!ignore) setVotesState({ key: votesKey, votes: {} }); });
    return () => { ignore = true; };
  }, [movie.content_id, voterId, votesKey]);
  const myVotes = votesState.key === votesKey ? votesState.votes : {};

  // Audience rating of this movie (US-008), refreshed whenever the list of reviews changes
  const reviewIdsKey = reviews.map(r => r.review_id || r.id).join(',');
  const [summaryState, setSummaryState] = useState({ key: null, data: null });
  const summaryKey = `${movie.content_id}|${reviewIdsKey}`;
  useEffect(() => {
    if (!isUuid(movie.content_id)) return undefined;
    let ignore = false;
    apiClient.get('/reviews/summary', { params: { content_id: movie.content_id } })
      .then(response => { if (!ignore) setSummaryState({ key: summaryKey, data: response.data }); })
      .catch(() => { if (!ignore) setSummaryState({ key: summaryKey, data: null }); });
    return () => { ignore = true; };
  }, [movie.content_id, summaryKey]);
  // Keep showing the previous numbers while a refresh is in flight
  const audienceSummary = isUuid(movie.content_id) ? summaryState.data : null;

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

    // The author is taken from the access token on the backend (FR-001)
    apiClient.post('/reviews', {
      content_id: movie.content_id,
      rating: Number(rating),
      review_text: text || null,
      contains_spoilers: text ? isSpoiler : false,
    })
      .then(response => {
        setReviews([response.data, ...reviews]);
        onReviewsChanged?.();
        setReviewText('');
        setIsSpoiler(false);
        setRating(10);
      })
      .catch(error => {
        const status = error.response?.status;
        const code = error.response?.data?.error?.code;
        if (status === 409) {
          setFormError(isUkr ? 'Ви вже залишили рецензію на цей фільм.' : 'You have already reviewed this movie.');
        } else if (code === 'CONTENT_NOT_WATCHED') {
          setFormError(isUkr
            ? 'Спершу позначте фільм як переглянутий, щоб оцінити його.'
            : 'Mark the title as watched before rating it.');
        } else if (status === 401) {
          setFormError(isUkr ? 'Сесія завершилась. Увійдіть ще раз.' : 'Your session has expired. Please log in again.');
          openAuth();
        } else {
          setFormError(error.response?.data?.error?.message
            || (isUkr ? 'Не вдалося опублікувати рецензію.' : 'Failed to publish review.'));
        }
      });
  };

  const setReviewCounts = (reviewId, counts) =>
    setReviews(prev => prev.map(rev => ((rev.review_id || rev.id) === reviewId ? { ...rev, ...counts } : rev)));
  const setMyVote = (reviewId, value) =>
    setVotesState(prev => ({ key: votesKey, votes: { ...(prev.key === votesKey ? prev.votes : {}), [reviewId]: value } }));

  // Support / don't support: optimistic update, rolled back with a message if the server refuses
  const handleVote = async (review, clicked) => {
    if (!isLoggedIn) {
      openAuth();
      return;
    }
    const reviewId = review.review_id;
    const from = myVotes[reviewId] || 0;
    const to = nextVote(from, clicked);
    const before = { likes: review.likes || 0, dislikes: review.dislikes || 0 };
    setVoteError('');
    setMyVote(reviewId, to);
    setReviewCounts(reviewId, applyVote(before, from, to));
    try {
      // Constant URL: the review id travels in the body
      const response = await apiClient.put('/reviews/votes', { review_id: reviewId, value: to });
      setReviewCounts(reviewId, { likes: response.data.likes, dislikes: response.data.dislikes });
    } catch (err) {
      setMyVote(reviewId, from);
      setReviewCounts(reviewId, before);
      const code = err.response?.data?.error?.code;
      if (code === 'ACCOUNT_BANNED') {
        setVoteError(err.response.data.error.message);
      } else if (err.response?.status === 401) {
        openAuth();
      } else {
        setVoteError(isUkr ? 'Не вдалося зберегти голос. Спробуйте ще раз.' : 'Could not save your vote. Please try again.');
      }
    }
  };

  const handleDeleteReview = async (reviewId) => {
    const isUkr = language === 'UKR';
    const confirmMessage = isUkr
      ? 'Ви впевнені, що хочете видалити цю рецензію? Цю дію неможливо скасувати.'
      : 'Are you sure you want to delete this review? This action cannot be undone.';
    if (!window.confirm(confirmMessage)) {
      return;
    }

    try {
      // Constant URL: the id travels as a query parameter (no user data in the request path)
      await apiClient.delete('/reviews', { params: { review_id: reviewId } });
      setReviews(prev => prev.filter(r => (r.review_id || r.id) !== reviewId));
      onReviewsChanged?.();
    } catch (err) {
      const errMsg = err.response?.data?.error?.message 
        || (isUkr ? 'Не вдалося видалити рецензію' : 'Failed to delete review');
      alert(errMsg);
    }
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

        <div className="flex items-center gap-3">
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

          {onToggleWatched && (
            <button
              onClick={() => onToggleWatched(movie.content_id || movie.id)}
              className={`px-4 py-2 rounded-xl font-bold text-sm transition-all shadow-sm flex items-center gap-2 ${
                isWatched 
                  ? 'bg-green-600 text-white shadow-md' 
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-green-600 hover:text-white'
              }`}
            >
              {isWatched ? (isUkr ? '✓ Переглянуто' : '✓ Watched') : (isUkr ? '👁️ Позначити як переглянуте' : '👁️ Mark as Watched')}
            </button>
          )}
        </div>
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
              <div><dt className="text-gray-500 dark:text-gray-400 font-semibold">TMDB:</dt><dd className="text-yellow-600 font-bold">★ {movie.rating} / 10</dd></div>
              {movie.runtime ? (
                <div>
                  <dt className="text-gray-500 dark:text-gray-400 font-semibold">{isUkr ? 'Тривалість:' : 'Runtime:'}</dt>
                  <dd className="text-gray-900 dark:text-gray-200 font-medium">
                    {movie.runtime} {isUkr ? 'хв' : 'min'}
                    {(movie.category || '').toLowerCase() === 'series' && (isUkr ? ' (серія)' : ' (episode)')}
                  </dd>
                </div>
              ) : null}
              <div>
                <dt className="text-gray-500 dark:text-gray-400 font-semibold">{isUkr ? 'Після титрів (глядачі):' : 'After Credits (audience):'}</dt>
                <dd className="text-cyan-600 dark:text-cyan-400 font-bold" data-testid="audience-rating">
                  {formatAudienceRating(audienceSummary, isUkr)}
                </dd>
              </div>
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
        ) : user?.ban ? (
          <BanNotice ban={user.ban} language={language} />
        ) : !isCatalogTitle ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {isUkr ? 'Оцінювати можна лише фільми з каталогу.' : 'Only catalog titles can be rated.'}
          </p>
        ) : myReview ? (
          <div className="bg-green-50 dark:bg-gray-700/50 border border-green-200 dark:border-gray-600 rounded-xl p-4 text-sm text-gray-700 dark:text-gray-300">
            {isUkr ? 'Ви вже оцінили цей фільм: ' : 'You have already rated this movie: '}
            <b>★ {myReview.rating}/10</b>
          </div>
        ) : !isWatched ? (
          // FR-003 / FR-004: only watched titles can be rated and reviewed
          <div className="bg-blue-50 dark:bg-gray-700/50 border border-blue-200 dark:border-gray-600 rounded-xl p-4 text-center">
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
              {isUkr
                ? 'Оцінити фільм і написати рецензію можна після того, як ви позначите його як переглянутий.'
                : 'You can rate and review this title after marking it as watched.'}
            </p>
            {onToggleWatched && (
              <button
                onClick={() => onToggleWatched(movie.content_id || movie.id)}
                className="px-5 py-2 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold rounded-lg text-sm transition-colors shadow"
              >
                {isUkr ? '👁️ Позначити як переглянуте' : '👁️ Mark as watched'}
              </button>
            )}
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

        {voteError && (
          <div role="alert" className="flex items-start justify-between gap-3 text-sm px-4 py-2 rounded-xl bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
            <span>{voteError}</span>
            <button type="button" onClick={() => setVoteError('')} aria-label={isUkr ? 'Закрити' : 'Close'} className="font-bold">✕</button>
          </div>
        )}

        {loadingReviews ? (
          <p className="text-gray-500 text-sm">{isUkr ? 'Завантаження рецензій...' : 'Loading reviews...'}</p>
        ) : reviews.length === 0 ? (
          <p className="text-gray-500 text-sm">
            {isUkr ? 'Ще немає жодної рецензії. Будьте першим!' : 'No reviews yet. Be the first!'}
          </p>
        ) : (
          reviews.map((rev) => {
            const reviewId = rev.review_id || rev.id;
            const isAuthor = user && (user.user_id === rev.user_id || user.id === rev.user_id);
            const isAdmin = user && user.role === 'admin';
            const canDelete = isAuthor || isAdmin;
            return (
              <div key={reviewId} className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-100 dark:border-gray-700">
                <div className="flex items-start gap-3">
                  <img src={rev.avatar || 'https://picsum.photos/50?random=99'} alt="avatar" className="w-10 h-10 rounded-full object-cover" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <h4 className="font-bold text-sm text-gray-900 dark:text-white">{rev.author_nickname || rev.author || (isUkr ? 'Глядач' : 'Viewer')}</h4>
                        <span className="px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300 font-bold text-xs rounded">
                          ★ {rev.rating}/10
                        </span>
                      </div>
                      <span className="text-xs text-gray-400">{rev.created_at ? new Date(rev.created_at).toLocaleDateString() : (isUkr ? 'щойно' : 'just now')}</span>
                    </div>
                    
                    <ReviewContent text={rev.review_text} isSpoiler={rev.contains_spoilers} language={language} />
                    
                    <div className="flex items-center justify-between gap-4 mt-3 text-xs text-gray-500">
                      <ReviewVotes
                        likes={rev.likes || 0}
                        dislikes={rev.dislikes || 0}
                        myVote={myVotes[reviewId] || 0}
                        isOwn={Boolean(isAuthor)}
                        isLoggedIn={isLoggedIn}
                        disabled={!isUuid(reviewId)}
                        language={language}
                        onVote={value => handleVote(rev, value)}
                      />

                      {canDelete && (
                        <button 
                          onClick={() => handleDeleteReview(reviewId)} 
                          className="hover:text-red-600 text-red-500 flex items-center gap-1 font-semibold transition-colors"
                          title={isUkr 
                            ? (isAdmin && !isAuthor ? 'Видалити як адміністратор' : 'Видалити власну рецензію') 
                            : (isAdmin && !isAuthor ? 'Delete as admin' : 'Delete your review')}
                          aria-label={isUkr ? 'Видалити рецензію' : 'Delete review'}
                        >
                          🗑️ {isUkr ? 'Видалити' : 'Delete'}
                          {isAdmin && !isAuthor && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded font-normal">
                              {isUkr ? 'адмін' : 'admin'}
                            </span>
                          )}
                        </button>
                      )}
                      {isAdmin && !isAuthor && isUuid(rev.user_id) && (
                        banDoneFor === rev.user_id ? (
                          <span role="status" className="text-red-600 dark:text-red-400 font-semibold">
                            {isUkr ? 'Автора заблоковано' : 'Author banned'}
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setBanTarget({ user_id: rev.user_id, nickname: rev.author_nickname || (isUkr ? 'автора' : 'the author') })}
                            className="hover:text-red-700 text-red-600 font-semibold transition-colors"
                          >
                            🚫 {isUkr ? 'Заблокувати автора' : 'Ban the author'}
                          </button>
                        )
                      )}
                    </div>
                    {/* FR-011: comments only for reviews stored on the backend */}
                    {isUuid(rev.review_id) && (
                      <ReviewComments
                        reviewId={rev.review_id}
                        isLoggedIn={isLoggedIn}
                        openAuth={openAuth}
                        user={user}
                        language={language}
                      />
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </section>

      {banTarget && (
        <BanUserDialog
          target={banTarget}
          language={language}
          onClose={() => setBanTarget(null)}
          onBanned={() => setBanDoneFor(banTarget.user_id)}
        />
      )}
    </div>
  );
}