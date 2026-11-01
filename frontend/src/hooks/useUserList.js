import { useEffect, useState } from 'react';
import apiClient from '../api/client';

// Shared core for per-user lists stored on the API (watchlist, watched list):
// loads the list for the current user, asks guests to log in, applies optimistic updates
// and rolls them back with a visible error if the server refuses.
export default function useUserList({ path, user, onAuthRequired }) {
  const userId = user?.user_id ?? null;
  const [state, setState] = useState({ userId: null, items: [] });
  const [error, setError] = useState(null); // 'UNAVAILABLE' | 'FAILED' | null

  useEffect(() => {
    if (!userId) return undefined;
    let ignore = false;
    apiClient.get(path)
      .then(response => {
        if (!ignore) setState({ userId, items: response.data.items || [] });
      })
      .catch(err => {
        console.warn(`List ${path} is unavailable:`, err);
        if (!ignore) setState({ userId, items: [] });
      });
    return () => {
      ignore = true;
    };
  }, [path, userId]);

  // Items of another (logged out) user are never shown
  const items = userId && state.userId === userId ? state.items : [];

  const requireUser = () => {
    if (userId) return true;
    onAuthRequired?.();
    return false;
  };

  const updateItems = update =>
    setState(current => ({ userId, items: update(current.userId === userId ? current.items : []) }));

  // Shows `nextItems` immediately, then runs `request`. If it fails (and the server is not already
  // in the desired state, see `isAlreadyDone`), the previous items come back and `error` is set.
  const applyOptimistic = async (nextItems, request, isAlreadyDone = () => false) => {
    const previous = items;
    setError(null);
    setState({ userId, items: nextItems });
    try {
      return await request();
    } catch (err) {
      if (!isAlreadyDone(err.response?.status)) {
        setState({ userId, items: previous });
        setError('FAILED');
      }
      return undefined;
    }
  };

  return {
    items,
    error,
    reportUnavailable: () => setError('UNAVAILABLE'),
    clearError: () => setError(null),
    requireUser,
    updateItems,
    applyOptimistic,
  };
}
