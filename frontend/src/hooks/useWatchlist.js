import { useEffect, useState } from 'react';
import apiClient from '../api/client';
import { isUuid } from '../utils/uuid';

// Watchlist backed by the API (FR-005). Updates are optimistic and rolled back if the server refuses.
export default function useWatchlist({ user, catalog = [], onAuthRequired }) {
  const userId = user?.user_id ?? null;
  const [state, setState] = useState({ userId: null, items: [] });
  const [error, setError] = useState(null); // 'UNAVAILABLE' | 'FAILED' | null

  useEffect(() => {
    if (!userId) return undefined;
    let ignore = false;
    apiClient.get('/watchlist')
      .then(response => {
        if (!ignore) setState({ userId, items: response.data.items || [] });
      })
      .catch(err => {
        console.warn('Watchlist is unavailable:', err);
        if (!ignore) setState({ userId, items: [] });
      });
    return () => {
      ignore = true;
    };
  }, [userId]);

  // Items of another (logged out) user are never shown
  const items = userId && state.userId === userId ? state.items : [];
  // Both ids are kept so callers may check either `movie.id` or `movie.content_id`
  const watchlistIds = items.flatMap(movie => [movie.id, movie.content_id]);

  const findMovie = movieOrId => {
    if (movieOrId && typeof movieOrId === 'object') return movieOrId;
    return [...items, ...catalog].find(movie => movie.id === movieOrId || movie.content_id === movieOrId);
  };

  const toggleWatchlist = async movieOrId => {
    if (!userId) {
      onAuthRequired?.();
      return;
    }
    const movie = findMovie(movieOrId);
    if (!movie || !isUuid(movie.content_id)) {
      setError('UNAVAILABLE');
      return;
    }

    const inList = items.some(item => item.content_id === movie.content_id);
    const previous = items;
    setError(null);
    setState({
      userId,
      items: inList ? items.filter(item => item.content_id !== movie.content_id) : [movie, ...items],
    });

    try {
      if (inList) {
        await apiClient.delete('/watchlist', { params: { content_id: movie.content_id } });
      } else {
        await apiClient.post('/watchlist', { content_id: movie.content_id });
      }
    } catch (err) {
      const status = err.response?.status;
      // The server is already in the desired state: keep the optimistic update
      if ((inList && status === 404) || (!inList && status === 409)) return;
      setState({ userId, items: previous });
      setError('FAILED');
    }
  };

  return {
    watchlistIds,
    watchlistMovies: items,
    toggleWatchlist,
    error,
    clearError: () => setError(null),
  };
}
