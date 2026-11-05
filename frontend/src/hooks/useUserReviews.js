import { useCallback, useEffect, useState } from 'react';
import apiClient from '../api/client';

// Reviews written by the current user. `refresh` reloads them after a review is published or deleted.
export default function useUserReviews({ user }) {
  const userId = user?.user_id ?? null;
  const [state, setState] = useState({ userId: null, items: [] });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!userId) return undefined;
    let ignore = false;
    apiClient.get('/reviews', { params: { user_id: userId, limit: 100 } })
      .then(response => { if (!ignore) setState({ userId, items: response.data.items || [] }); })
      .catch(() => { if (!ignore) setState({ userId, items: [] }); });
    return () => { ignore = true; };
  }, [userId, version]);

  const loaded = Boolean(userId) && state.userId === userId;
  const refresh = useCallback(() => setVersion(v => v + 1), []);
  return { reviews: loaded ? state.items : [], loaded, refresh };
}
