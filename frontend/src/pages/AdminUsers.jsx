import { useCallback, useEffect, useState } from 'react';
import apiClient from '../api/client';
import BanUserDialog from '../components/BanUserDialog';
import { banStatusLabel } from '../utils/ban';

// FR-009 / US-006: administrator's list of users with search, ban and unban
export default function AdminUsers({ language = 'UKR' }) {
  const isUkr = language === 'UKR';
  const [query, setQuery] = useState('');
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [banTarget, setBanTarget] = useState(null);

  const load = useCallback(async (search) => {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/admin/users', { params: search ? { q: search } : {} });
      setUsers(response.data.items);
      setTotal(response.data.total);
    } catch {
      setError(isUkr ? 'Не вдалося завантажити користувачів.' : 'Failed to load users.');
    } finally {
      setLoading(false);
    }
  }, [isUkr]);

  useEffect(() => {
    const timer = setTimeout(() => load(query.trim()), 300);
    return () => clearTimeout(timer);
  }, [query, load]);

  const unban = async (user) => {
    setError('');
    try {
      // Constant URL: the user id travels as a query parameter
      await apiClient.delete('/admin/bans', { params: { user_id: user.user_id } });
      load(query.trim());
    } catch {
      setError(isUkr ? 'Не вдалося розблокувати користувача.' : 'Failed to lift the ban.');
    }
  };

  return (
    <section className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-black text-gray-900 dark:text-white mb-1">{isUkr ? 'Користувачі' : 'Users'}</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
        {isUkr
          ? 'Заблокований користувач не може писати рецензії, ставити оцінки й коментувати, але бачить причину й термін блокування.'
          : 'A banned user cannot review, rate or comment, and sees the reason and the period of the ban.'}
      </p>

      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={isUkr ? 'Пошук за нікнеймом або email' : 'Search by nickname or email'}
        aria-label={isUkr ? 'Пошук користувачів' : 'Search users'}
        className="w-full sm:w-96 mb-4 px-4 py-2 rounded-full border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
      />

      {error && <p role="alert" className="mb-3 text-sm text-red-600 dark:text-red-400 font-semibold">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500">{isUkr ? 'Завантаження…' : 'Loading…'}</p>
      ) : users.length === 0 ? (
        <p className="text-sm text-gray-500">{isUkr ? 'Нікого не знайдено.' : 'No users found.'}</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-100 dark:border-gray-700">
          <table className="w-full text-sm text-left bg-white dark:bg-gray-800">
            <thead className="bg-gray-50 dark:bg-gray-700/50 text-gray-500 dark:text-gray-400 text-xs uppercase">
              <tr>
                <th className="px-4 py-3">{isUkr ? 'Нікнейм' : 'Nickname'}</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">{isUkr ? 'Роль' : 'Role'}</th>
                <th className="px-4 py-3">{isUkr ? 'Стан' : 'Status'}</th>
                <th className="px-4 py-3"><span className="sr-only">{isUkr ? 'Дії' : 'Actions'}</span></th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.user_id} className="border-t border-gray-100 dark:border-gray-700 text-gray-800 dark:text-gray-200">
                  <td className="px-4 py-3 font-semibold">{user.nickname}</td>
                  <td className="px-4 py-3">{user.email}</td>
                  <td className="px-4 py-3">{user.role === 'admin' ? (isUkr ? 'адмін' : 'admin') : (isUkr ? 'користувач' : 'user')}</td>
                  <td className={`px-4 py-3 ${user.ban ? 'text-red-600 dark:text-red-400 font-semibold' : ''}`}>
                    {banStatusLabel(user.ban, language)}
                    {user.ban?.reason && <span className="block text-xs font-normal text-gray-500 dark:text-gray-400">{user.ban.reason}</span>}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    {user.role !== 'admin' && (user.ban ? (
                      <button
                        type="button"
                        onClick={() => unban(user)}
                        aria-label={isUkr ? `Розблокувати ${user.nickname}` : `Unban ${user.nickname}`}
                        className="px-3 py-1.5 rounded-lg bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 font-bold text-xs"
                      >
                        {isUkr ? 'Розблокувати' : 'Unban'}
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setBanTarget(user)}
                        aria-label={isUkr ? `Заблокувати ${user.nickname}` : `Ban ${user.nickname}`}
                        className="px-3 py-1.5 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-300 font-bold text-xs"
                      >
                        {isUkr ? 'Заблокувати' : 'Ban'}
                      </button>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="px-4 py-2 text-xs text-gray-400">{isUkr ? `Усього: ${total}` : `Total: ${total}`}</p>
        </div>
      )}

      {banTarget && (
        <BanUserDialog
          target={banTarget}
          language={language}
          onClose={() => setBanTarget(null)}
          onBanned={() => load(query.trim())}
        />
      )}
    </section>
  );
}
