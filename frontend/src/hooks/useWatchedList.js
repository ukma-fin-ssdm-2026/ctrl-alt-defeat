import apiClient from '../api/client';
import { isUuid } from '../utils/uuid';
import useUserList from './useUserList';

// "Watched" list backed by the API (FR-006)
export default function useWatchedList({ user, catalog = [], onAuthRequired }) {
  const list = useUserList({ path: '/users/me/watched', user, onAuthRequired });
  const { items } = list;

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
    if (!list.requireUser()) return;
    const contentId = resolveContentId(movieOrId);
    if (!isUuid(contentId)) {
      list.reportUnavailable();
      return;
    }

    const watched = items.some(item => item.content_id === contentId);
    const movie = typeof movieOrId === 'object' ? movieOrId : catalog.find(m => m.content_id === contentId) || {};
    const response = await list.applyOptimistic(
      watched ? items.filter(item => item.content_id !== contentId) : [{ ...movie, content_id: contentId }, ...items],
      // Constant URL: the id travels as a query parameter (no user data in the request path)
      () => watched
        ? apiClient.delete('/users/me/watched', { params: { content_id: contentId } })
        : apiClient.post('/users/me/watched', { content_id: contentId }),
      // Already removed on the server: keep the optimistic state
      status => watched && status === 404
    );

    // Replace the optimistic item with the server version (title, poster, dates)
    if (!watched && response?.data) {
      updateServerItem(response.data);
    }
  };

  const updateServerItem = serverItem =>
    list.updateItems(current => [serverItem, ...current.filter(item => item.content_id !== serverItem.content_id)]);

  return {
    watchedMovies: items,
    isWatched,
    toggleWatched,
    error: list.error,
    clearError: list.clearError,
  };
}
