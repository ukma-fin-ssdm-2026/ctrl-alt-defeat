import { useState } from 'react';
import apiClient from '../api/client';

// The link from the "Forgot password?" email opens /reset-password?token=...; here the new password is set
export default function ResetPasswordModal({ token, language = 'UKR', close, onDone }) {
  const isUkr = language === 'UKR';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const errorText = code => {
    if (code === 'RESET_TOKEN_EXPIRED') {
      return isUkr
        ? 'Посилання застаріло (діє 1 годину). Запросіть нове у вікні входу: «Забули пароль?».'
        : 'The link has expired (it works for 1 hour). Request a new one in the login window: "Forgot password?".';
    }
    if (code === 'INVALID_RESET_TOKEN') {
      return isUkr
        ? 'Посилання недійсне або вже використане. Запросіть нове у вікні входу.'
        : 'The link is invalid or already used. Request a new one in the login window.';
    }
    if (code === 'VALIDATION_ERROR') {
      return isUkr ? 'Пароль — щонайменше 8 символів.' : 'The password needs at least 8 characters.';
    }
    return isUkr ? 'Не вдалося змінити пароль. Спробуйте ще раз.' : 'Could not change the password. Please try again.';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirm) {
      setError(isUkr ? 'Паролі не збігаються!' : 'Passwords do not match!');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await apiClient.post('/auth/reset-password', { token, new_password: password });
      onDone?.();
    } catch (err) {
      setError(errorText(err.response?.data?.error?.code));
      setSaving(false);
    }
  };

  const inputClass =
    'border border-gray-300 dark:border-gray-600 p-3 rounded-xl bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div className="bg-white dark:bg-gray-800 w-full max-w-md rounded-2xl shadow-xl p-8 relative border border-gray-100 dark:border-gray-700">
        <button onClick={close} aria-label={isUkr ? 'Закрити' : 'Close'} className="absolute top-4 right-4 text-gray-400 hover:text-black dark:hover:text-white text-xl">
          ✕
        </button>
        <h2 className="text-3xl font-black mb-6 text-center text-gray-900 dark:text-white">
          {isUkr ? 'Новий пароль' : 'New password'}
        </h2>
        {error && <p role="alert" className="text-red-500 text-sm mb-4 text-center font-semibold">{error}</p>}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={isUkr ? 'Новий пароль' : 'New password'}
            autoComplete="new-password"
            required
            minLength={8}
            className={inputClass}
          />
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder={isUkr ? 'Повторіть пароль' : 'Repeat the password'}
            autoComplete="new-password"
            required
            minLength={8}
            className={inputClass}
          />
          <p className="-mt-2 text-xs text-gray-500 dark:text-gray-400">
            {isUkr
              ? 'Щонайменше 8 символів. Після зміни всі ваші сесії на інших пристроях завершаться.'
              : 'At least 8 characters. All your sessions on other devices will end.'}
          </p>
          <button
            type="submit"
            disabled={saving}
            className="bg-yellow-500 text-gray-900 font-bold py-3 rounded-xl mt-2 hover:bg-yellow-600 transition shadow-sm disabled:opacity-50"
          >
            {saving ? (isUkr ? 'Збереження...' : 'Saving...') : (isUkr ? 'Зберегти пароль' : 'Save password')}
          </button>
        </form>
      </div>
    </div>
  );
}
