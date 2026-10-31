import { useState } from 'react';

export default function AuthModal({ close, onLogin, language = 'UKR' }) {
  const [isLogin, setIsLogin] = useState(true);
  
  const [email, setEmail] = useState('admin@gmail.com');
  const [password, setPassword] = useState('password12345');
  const [error, setError] = useState('');

  const isUkr = language === 'UKR';

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (isLogin) {
      const success = onLogin(email, password);
      if (!success) {
        setError(isUkr ? 'Неправильний логін або пароль.' : 'Invalid email or password.');
      }
    } else {
      alert(isUkr ? 'Реєстрація успішна (демо)! Тепер увійдіть.' : 'Registration successful (demo)! Please log in.');
      setIsLogin(true);
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

        {}
        {isLogin && (
          <div className="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-700/50 text-yellow-800 dark:text-yellow-400 text-xs p-3 rounded-lg mb-6 text-center">
            {isUkr ? 'Демо доступ:' : 'Demo access:'} <b>admin@gmail.com</b> / <b>password12345</b>
          </div>
        )}

        {}
        {error && <p className="text-red-500 text-sm mb-4 text-center font-semibold">{error}</p>}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {!isLogin && (
            <input 
              type="text" 
              placeholder={isUkr ? "Ваш нікнейм (Ім'я)" : "Your Nickname"} 
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
            className="border border-gray-300 dark:border-gray-600 p-3 rounded-xl bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-yellow-500 focus:outline-none" 
          />
          
          <button type="submit" className="bg-yellow-500 text-gray-900 font-bold py-3 rounded-xl mt-4 hover:bg-yellow-600 transition shadow-sm">
            {isLogin 
              ? (isUkr ? 'Увійти' : 'Login') 
              : (isUkr ? 'Зареєструватись' : 'Sign Up')}
          </button>
        </form>

        <p className="text-center mt-6 text-sm text-gray-600 dark:text-gray-400">
          {isLogin 
            ? (isUkr ? 'Немає акаунту? ' : 'No account? ') 
            : (isUkr ? 'Вже зареєстровані? ' : 'Already have an account? ')}
          <span 
            className="text-yellow-600 dark:text-yellow-400 font-bold cursor-pointer hover:underline ml-1"
            onClick={() => { setIsLogin(!isLogin); setError(''); }}
          >
            {isLogin 
              ? (isUkr ? 'Створити' : 'Sign up') 
              : (isUkr ? 'Увійти' : 'Login')}
          </span>
        </p>
      </div>
    </div>
  );
}