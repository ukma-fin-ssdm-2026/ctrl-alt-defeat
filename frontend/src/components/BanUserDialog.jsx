import { useState } from 'react';
import apiClient from '../api/client';

const MAX_DAYS = 365;
const MAX_REASON = 500;

// FR-009: an administrator bans a user temporarily (1-365 days) or permanently, with a message
export default function BanUserDialog({ target, language = 'UKR', onClose, onBanned }) {
  const isUkr = language === 'UKR';
  const [banType, setBanType] = useState('temporary');
  const [days, setDays] = useState(7);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const daysValid = Number.isInteger(Number(days)) && Number(days) >= 1 && Number(days) <= MAX_DAYS;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (banType === 'temporary' && !daysValid) {
      setError(isUkr ? `Термін — від 1 до ${MAX_DAYS} днів.` : `The period must be 1 to ${MAX_DAYS} days.`);
      return;
    }
    setError('');
    setSaving(true);
    try {
      // Constant URL: the user id travels in the request body
      const response = await apiClient.post('/admin/bans', {
        user_id: target.user_id,
        ban_type: banType,
        ...(banType === 'temporary' ? { duration_days: Number(days) } : {}),
        ...(reason.trim() ? { reason: reason.trim() } : {}),
      });
      onBanned?.(response.data);
      onClose();
    } catch (err) {
      const code = err.response?.data?.error?.code;
      if (code === 'CANNOT_BAN_ADMIN') setError(isUkr ? 'Адміністратора заблокувати не можна.' : 'Administrators cannot be banned.');
      else if (code === 'CANNOT_BAN_SELF') setError(isUkr ? 'Не можна заблокувати себе.' : 'You cannot ban yourself.');
      else setError(isUkr ? 'Не вдалося заблокувати користувача.' : 'Failed to ban the user.');
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="ban-dialog-title"
        className="bg-white dark:bg-gray-800 w-full max-w-md rounded-2xl shadow-xl p-6 border border-gray-100 dark:border-gray-700"
      >
        <h2 id="ban-dialog-title" className="text-xl font-black mb-4 text-gray-900 dark:text-white">
          {isUkr ? `Заблокувати ${target.nickname}` : `Ban ${target.nickname}`}
        </h2>
        <form noValidate onSubmit={handleSubmit} className="flex flex-col gap-4 text-sm text-gray-800 dark:text-gray-200">
          <fieldset className="flex flex-col gap-2">
            <legend className="font-semibold mb-1">{isUkr ? 'Тип блокування' : 'Ban type'}</legend>
            <label className="flex items-center gap-2">
              <input type="radio" name="ban_type" value="temporary" checked={banType === 'temporary'} onChange={() => setBanType('temporary')} />
              {isUkr ? 'Тимчасове' : 'Temporary'}
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="ban_type" value="permanent" checked={banType === 'permanent'} onChange={() => setBanType('permanent')} />
              {isUkr ? 'Назавжди' : 'Permanent'}
            </label>
          </fieldset>

          {banType === 'temporary' && (
            <label className="flex flex-col gap-1">
              <span className="font-semibold">{isUkr ? 'Термін, днів' : 'Duration, days'}</span>
              <input
                type="number"
                min="1"
                max={MAX_DAYS}
                value={days}
                onChange={(e) => setDays(e.target.value)}
                className="border border-gray-300 dark:border-gray-600 p-2 rounded-lg bg-gray-50 dark:bg-gray-700"
              />
            </label>
          )}

          <label className="flex flex-col gap-1">
            <span className="font-semibold">{isUkr ? 'Повідомлення користувачу (причина)' : 'Message to the user (reason)'}</span>
            <textarea
              rows="3"
              value={reason}
              maxLength={MAX_REASON}
              onChange={(e) => setReason(e.target.value)}
              placeholder={isUkr ? 'Наприклад: спойлери без позначки' : 'For example: unmarked spoilers'}
              className="border border-gray-300 dark:border-gray-600 p-2 rounded-lg bg-gray-50 dark:bg-gray-700"
            />
          </label>

          {error && <p role="alert" className="text-red-600 dark:text-red-400 font-semibold">{error}</p>}

          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg text-gray-600 dark:text-gray-300 hover:underline">
              {isUkr ? 'Скасувати' : 'Cancel'}
            </button>
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-bold">
              {isUkr ? 'Заблокувати' : 'Ban'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
