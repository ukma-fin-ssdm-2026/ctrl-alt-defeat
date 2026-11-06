import { useEffect, useState } from 'react';
import apiClient from '../api/client';

export const POLL_MS = 3000;

// FR-012: the administrator updates the catalog from TMDB (movies, series, cartoons) in the background
export default function AdminCatalogSync({ language = 'UKR' }) {
  const isUkr = language === 'UKR';
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const running = status?.state === 'running';

  // Load the state once, then poll while the update is running
  useEffect(() => {
    let ignore = false;
    const load = () => apiClient.get('/admin/catalog/sync')
      .then(response => { if (!ignore) setStatus(response.data); })
      .catch(() => { if (!ignore) setError(isUkr ? 'Не вдалося отримати стан оновлення.' : 'Could not load the update state.'); });
    if (status === null) {
      load();
      return () => { ignore = true; };
    }
    if (!running) return () => { ignore = true; };
    const timer = setTimeout(load, POLL_MS);
    return () => { ignore = true; clearTimeout(timer); };
  }, [status, running, isUkr]);

  const start = async () => {
    setError('');
    try {
      const response = await apiClient.post('/admin/catalog/sync');
      setStatus(response.data);
    } catch (err) {
      const code = err.response?.data?.error?.code;
      if (code === 'SYNC_IN_PROGRESS') {
        setStatus(current => ({ ...current, state: 'running' }));
      } else if (code === 'TMDB_NOT_CONFIGURED') {
        setStatus(current => ({ ...current, configured: false }));
      } else {
        setError(isUkr ? 'Не вдалося запустити оновлення.' : 'Could not start the update.');
      }
    }
  };

  const time = value => (value ? new Date(value).toLocaleString(isUkr ? 'uk-UA' : 'en-GB') : '');

  return (
    <section aria-labelledby="catalog-sync-heading" className="max-w-5xl mx-auto mb-8 p-5 rounded-2xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
        <div>
          <h2 id="catalog-sync-heading" className="text-lg font-black text-gray-900 dark:text-white">
            {isUkr ? 'Каталог TMDB' : 'TMDB catalog'}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {isUkr
              ? 'Імпорт 100 популярних фільмів, 100 серіалів і 100 мультфільмів із постерами, описами, жанрами й тривалістю. Наявні фільми оновлюються, нічого не видаляється.'
              : 'Imports 100 popular movies, 100 series and 100 cartoons with posters, descriptions, genres and runtime. Existing titles are updated, nothing is deleted.'}
          </p>
        </div>
        <button
          type="button"
          onClick={start}
          disabled={!status || running || status.configured === false}
          className="shrink-0 px-4 py-2 rounded-xl bg-yellow-500 hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900 text-sm font-bold transition-colors"
        >
          {running ? (isUkr ? 'Оновлення…' : 'Updating…') : (isUkr ? 'Оновити каталог з TMDB' : 'Update from TMDB')}
        </button>
      </div>

      <div role="status" className="mt-3 text-sm">
        {status?.configured === false && (
          <p className="text-amber-700 dark:text-amber-300">
            {isUkr
              ? 'Ключ TMDB не налаштовано: додайте TMDB_API_KEY у Render → Environment.'
              : 'TMDB key is not configured: add TMDB_API_KEY in Render → Environment.'}
          </p>
        )}
        {running && (
          <p className="text-gray-600 dark:text-gray-300">
            {isUkr ? 'Іде оновлення, це займе близько хвилини…' : 'Updating, this takes about a minute…'}
          </p>
        )}
        {status?.state === 'done' && (
          <p className="text-green-700 dark:text-green-300">
            {isUkr
              ? `Готово ${time(status.finished_at)}: додано ${status.added}, оновлено ${status.updated}${status.skipped ? `, пропущено ${status.skipped}` : ''}${status.placeholders_removed ? `, прибрано тестових фільмів ${status.placeholders_removed}` : ''}${status.placeholders_kept ? ` (${status.placeholders_kept} залишено: ними вже користувались)` : ''}. Оновіть сторінку, щоб побачити нові фільми.`
              : `Done ${time(status.finished_at)}: ${status.added} added, ${status.updated} updated${status.skipped ? `, ${status.skipped} skipped` : ''}${status.placeholders_removed ? `, ${status.placeholders_removed} placeholder titles removed` : ''}${status.placeholders_kept ? ` (${status.placeholders_kept} kept: already used)` : ''}. Reload the page to see new titles.`}
          </p>
        )}
        {status?.state === 'failed' && (
          <p className="text-red-700 dark:text-red-300">
            {isUkr ? 'Оновлення не вдалося: ' : 'The update failed: '}{status.error}
          </p>
        )}
        {error && <p className="text-red-700 dark:text-red-300">{error}</p>}
      </div>
    </section>
  );
}
