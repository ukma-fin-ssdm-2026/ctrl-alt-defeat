import { useEffect, useState } from 'react';
import apiClient from '../api/client';

export default function AuthModal({ close, onLogin, language = 'UKR', notice = '' }) {
  const [isLogin, setIsLogin] = useState(true);
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [successInfo, setSuccessInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  // FR-001: address that still needs confirmation, for "send the link again"
  const [unverifiedEmail, setUnverifiedEmail] = useState('');
  const [resendStatus, setResendStatus] = useState('');
  // Demo accounts come from the server configuration (DEMO_MODE), never from the frontend code
  const [demoAccounts, setDemoAccounts] = useState([]);

  const isUkr = language === 'UKR';

  useEffect(() => {
    let active = true;
    apiClient
      .get('/auth/demo-accounts')
      .then(response => {
        if (active && response.data?.enabled) setDemoAccounts(response.data.accounts || []);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const fillDemoAccount = account => {
    setIsLogin(true);
    setEmail(account.email);
    setPassword(account.password);
    setError('');
    setSuccessInfo(null);
  };

  const demoRoleLabel = role =>
    role === 'admin' ? (isUkr ? 'Адміністратор' : 'Administrator') : isUkr ? 'Користувач' : 'User';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessInfo(null);
    setUnverifiedEmail('');
    setResendStatus('');
    setLoading(true);

    if (isLogin) {
      const result = await onLogin(email, password);
      setLoading(false);
      if (!result.success) {
        if (result.code === 'EMAIL_NOT_VERIFIED') {
          setError(isUkr 
            ? 'Будь ласка, підтвердіть вашу пошту перед входом. Скористайтеся посиланням активації.' 
            : 'Please verify your email before logging in. Use your activation link.');
          setUnverifiedEmail(email.trim().toLowerCase());
        } else if (result.code === 'ACCOUNT_BANNED') {
          setError(isUkr 
            ? 'Ваш обліковий запис заблоковано адміністратором.' 
            : 'Your account has been suspended by an administrator.');
        } else {
          setError(isUkr 
            ? 'Неправильний email або пароль.' 
            : 'Invalid email or password.');
        }
      }
    } else {
      try {
        const response = await apiClient.post('/auth/register', {
          email: email.trim().toLowerCase(),
          nickname: nickname.trim(),
          password,
        });
        setLoading(false);
        const data = response.data;
        setSuccessInfo({
          email: data.email,
          token: data.verification_token,
          message: isUkr
            ? `Акаунт створено! Ми надіслали лист із посиланням на ${data.email}. Перейдіть за ним, щоб активувати акаунт.`
            : `Account created! We sent a link to ${data.email}. Open it to activate your account.`,
        });
        setUnverifiedEmail(data.email);
      } catch (err) {
        setLoading(false);
        const errCode = err.response?.data?.error?.code || err.response?.data?.detail?.code;
        if (errCode === 'EMAIL_ALREADY_EXISTS') {
          setError(isUkr ? 'Цей email уже зареєстровано.' : 'This email is already registered.');
        } else if (errCode === 'NICKNAME_ALREADY_EXISTS') {
          setError(isUkr ? 'Цей нікнейм уже зайнято.' : 'This nickname is already taken.');
        } else {
          setError(err.response?.data?.error?.message || (isUkr ? 'Помилка реєстрації.' : 'Registration error.'));
        }
      }
    }
  };

  const handleResend = async () => {
    setResendStatus('');
    try {
      await apiClient.post('/auth/resend-verification', { email: unverifiedEmail });
      setResendStatus(isUkr ? `Лист надіслано ще раз на ${unverifiedEmail}.` : `The link was sent again to ${unverifiedEmail}.`);
    } catch {
      setResendStatus(isUkr ? 'Не вдалося надіслати лист. Спробуйте пізніше.' : 'Could not send the email. Please try later.');
    }
  };

  const handleVerifyNow = async (token) => {
    setLoading(true);
    setError('');
    try {
      await apiClient.get('/auth/verify', { params: { token } });
      setLoading(false);
      setSuccessInfo(null);
      setIsLogin(true);
      setError('');
      alert(isUkr ? '✅ Пошту успішно підтверджено! Тепер ви можете увійти.' : '✅ Email verified! You can now log in.');
    } catch {
      setLoading(false);
      setError(isUkr ? 'Недійсний токен активації.' : 'Invalid verification token.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div className="bg-white dark:bg-gray-800 w-full max-w-md rounded-2xl shadow-xl p-8 relative border border-gray-100 dark:border-gray-700">
        <button onClick={close} className="absolute top-4 right-4 text-gray-400 hover:text-black dark:hover:text-white text-xl">
          ✕
        </button>
        
        <h2 className="text-3xl font-black mb-6 text-center text-gray-900 dark:text-white">
          {isLogin 
            ? (isUkr ? 'Вхід' : 'Login') 
            : (isUkr ? 'Реєстрація' : 'Register')}
        </h2>

        {notice && (
          <p role="status" className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700/50 text-blue-800 dark:text-blue-300 text-sm p-3 rounded-lg mb-4 text-center font-semibold">
            {notice}
          </p>
        )}

        {isLogin && demoAccounts.length > 0 && (
          <div
            aria-label={isUkr ? 'Демо доступ' : 'Demo access'}
            className="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-700/50 text-yellow-800 dark:text-yellow-400 text-xs p-3 rounded-lg mb-6 text-center"
          >
            <p className="font-semibold mb-1">{isUkr ? 'Демо доступ:' : 'Demo access:'}</p>
            {demoAccounts.map(account => (
              <p key={account.email} className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1">
                <span>
                  {demoRoleLabel(account.role)}: <b>{account.email}</b> / <b>{account.password}</b>
                </span>
                <button
                  type="button"
                  onClick={() => fillDemoAccount(account)}
                  className="underline font-bold hover:text-yellow-900 dark:hover:text-yellow-200"
                >
                  {isUkr ? 'Підставити' : 'Use'}
                </button>
              </p>
            ))}
          </div>
        )}

        {successInfo && (
          <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 text-green-800 dark:text-green-300 text-xs p-4 rounded-xl mb-4 text-center">
            <p className="font-semibold mb-2">{successInfo.message}</p>
            {successInfo.token && (
              <button
                type="button"
                onClick={() => handleVerifyNow(successInfo.token)}
                className="mt-2 bg-green-600 hover:bg-green-700 text-white font-bold py-1.5 px-4 rounded-lg shadow-sm transition text-xs"
              >
                {isUkr ? '✉️ Підтвердити email (демо в 1 клік)' : '✉️ Confirm email (1-click demo)'}
              </button>
            )}
          </div>
        )}

        {error && <p className="text-red-500 text-sm mb-4 text-center font-semibold">{error}</p>}

        {unverifiedEmail && (
          <div className="mb-4 text-center text-xs text-gray-600 dark:text-gray-300">
            <button type="button" onClick={handleResend} className="font-bold text-yellow-600 dark:text-yellow-400 hover:underline">
              {isUkr ? '✉️ Надіслати лист ще раз' : '✉️ Send the link again'}
            </button>
            {resendStatus && <p role="status" className="mt-1">{resendStatus}</p>}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {!isLogin && (
            <input 
              type="text" 
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder={isUkr ? "Ваш нікнейм (Ім'я)" : "Your Nickname"} 
              required
              minLength={2}
              className="border border-gray-300 dark:border-gray-600 p-3 rounded-xl bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none" 
            />
          )}
          <input 
            type="email" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email" 
            required
            className="border border-gray-300 dark:border-gray-600 p-3 rounded-xl bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none" 
          />
          <input 
            type="password" 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={isUkr ? "Пароль" : "Password"} 
            required
            minLength={6}
            className="border border-gray-300 dark:border-gray-600 p-3 rounded-xl bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none" 
          />
          
          <button 
            type="submit" 
            disabled={loading}
            className="bg-yellow-500 text-gray-900 font-bold py-3 rounded-xl mt-4 hover:bg-yellow-600 transition shadow-sm disabled:opacity-50"
          >
            {loading ? (isUkr ? 'Обробка...' : 'Processing...') : (isLogin 
              ? (isUkr ? 'Увійти' : 'Login') 
              : (isUkr ? 'Зареєструватись' : 'Sign Up'))}
          </button>
        </form>

        <p className="text-center mt-6 text-sm text-gray-600 dark:text-gray-400">
          {isLogin 
            ? (isUkr ? 'Немає акаунту? ' : 'No account? ') 
            : (isUkr ? 'Вже зареєстровані? ' : 'Already have an account? ')}
          <button
            type="button"
            className="text-yellow-600 dark:text-yellow-400 font-bold cursor-pointer hover:underline ml-1"
            onClick={() => { setIsLogin(!isLogin); setError(''); setSuccessInfo(null); }}
          >
            {isLogin
              ? (isUkr ? 'Створити' : 'Sign up')
              : (isUkr ? 'Увійти' : 'Login')}
          </button>
        </p>
      </div>
    </div>
  );
}