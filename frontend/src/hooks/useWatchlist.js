import apiClient from '../api/client';
import { isUuid } from '../utils/uuid';
import useUserList from './useUserList';

// Watchlist backed by the API (FR-005)
export default function useWatchlist({ user, catalog = [], onAuthRequired }) {
  const list = useUserList({ path: '/watchlist', user, onAuthRequired });
  const { items } = list;
  // Both ids are kept so callers may check either `movie.id` or `movie.content_id`
  const watchlistIds = items.flatMap(movie => [movie.id, movie.content_id]);

  const findMovie = movieOrId => {
    if (movieOrId && typeof movieOrId === 'object') return movieOrId;
    return [...items, ...catalog].find(movie => movie.id === movieOrId || movie.content_id === movieOrId);
  };

  const toggleWatchlist = async movieOrId => {
    if (!list.requireUser()) return;
    const movie = findMovie(movieOrId);
    if (!movie || !isUuid(movie.content_id)) {
      list.reportUnavailable();
      return;
    }

    const inList = items.some(item => item.content_id === movie.content_id);
    await list.applyOptimistic(
      inList ? items.filter(item => item.content_id !== movie.content_id) : [movie, ...items],
      () => inList
        ? apiClient.delete('/watchlist', { params: { content_id: movie.content_id } })
        : apiClient.post('/watchlist', { content_id: movie.content_id }),
      // The server is already in the desired state: keep the optimistic update
      status => (inList && status === 404) || (!inList && status === 409)
    );
  };

  return {
    watchlistIds,
    watchlistMovies: items,
    loaded: list.loaded,
    toggleWatchlist,
    error: list.error,
    clearError: list.clearError,
  };
}
