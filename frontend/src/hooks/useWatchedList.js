import { useEffect, useState } from 'react';
import apiClient from '../api/client';
import { isUuid } from '../utils/uuid';

// "Watched" list backed by the API (FR-006). Optimistic updates with rollback and a visible error.
export default function useWatchedList({ user, catalog = [], onAuthRequired }) {
  const userId = user?.user_id ?? null;
  const [state, setState] = useState({ userId: null, items: [] });
  const [error, setError] = useState(null); // 'UNAVAILABLE' | 'FAILED' | null

  useEffect(() => {
    if (!userId) return undefined;
    let ignore = false;
    apiClient.get('/users/me/watched')
      .then(response => {
        if (!ignore) setState({ userId, items: response.data.items || [] });
      })
      .catch(err => {
        console.warn('Watched list is unavailable:', err);
        if (!ignore) setState({ userId, items: [] });
      });
    return () => {
      ignore = true;
    };
  }, [userId]);

  const items = userId && state.userId === userId ? state.items : [];

  const resolveContentId = movieOrId => {
    if (movieOrId && typeof movieOrId === 'object') return movieOrId.content_id;
    const movie = catalog.find(m => m.id === movieOrId || m.content_id === movieOrId);
    return movie ? movie.content_id : movieOrId;
  };

  const isWatched = movieOrId => {
    const contentId = resolveContentId(movieOrId);
    return Boolean(contentId) && items.some(item => item.content_id === contentId);
  };

  const toggleWatched = async movieOrId => {
    if (!userId) {
      onAuthRequired?.();
      return;
    }
    const contentId = resolveContentId(movieOrId);
    if (!isUuid(contentId)) {
      setError('UNAVAILABLE');
      return;
    }

    const watched = items.some(item => item.content_id === contentId);
    const previous = items;
    const movie = typeof movieOrId === 'object' ? movieOrId : catalog.find(m => m.content_id === contentId) || {};
    setError(null);
    setState({
      userId,
      items: watched
        ? items.filter(item => item.content_id !== contentId)
        : [{ ...movie, content_id: contentId }, ...items],
    });

    try {
      if (watched) {
        // Constant URL: the id travels as a query parameter (no user data in the request path)
        await apiClient.delete('/users/me/watched', { params: { content_id: contentId } });
      } else {
        const response = await apiClient.post('/users/me/watched', { content_id: contentId });
        // Replace the optimistic item with the server version (has title, poster, dates)
        setState(current => ({
          userId,
          items: [response.data, ...current.items.filter(item => item.content_id !== contentId)],
        }));
      }
    } catch (err) {
      // Already removed on the server: keep the optimistic state
      if (watched && err.response?.status === 404) return;
      setState({ userId, items: previous });
      setError('FAILED');
    }
  };

  return {
    watchedMovies: items,
    isWatched,
    toggleWatched,
    error,
    clearError: () => setError(null),
  };
}
