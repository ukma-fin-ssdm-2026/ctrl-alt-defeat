import { useState } from 'react';

export default function AuthModal({ close }) {
  const [isLogin, setIsLogin] = useState(true);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div className="bg-white dark:bg-gray-800 w-full max-w-md rounded-lg shadow-xl p-6 relative">
        <button onClick={close} className="absolute top-4 right-4 text-gray-400 hover:text-black dark:hover:text-white">
          ✕
        </button>
        
        <h2 className="text-2xl font-bold mb-4 text-center">
          {isLogin ? 'Вхід' : 'Реєстрація'}
        </h2>

        <form className="flex flex-col gap-4">
          {!isLogin && (
            <input type="text" placeholder="Ваш нікнейм (Ім'я)" className="border p-2 rounded dark:bg-gray-700 dark:border-gray-600" />
          )}
          <input type="email" placeholder="Email" className="border p-2 rounded dark:bg-gray-700 dark:border-gray-600" />
          <input type="password" placeholder="Пароль" className="border p-2 rounded dark:bg-gray-700 dark:border-gray-600" />
          
          <button className="bg-blue-600 text-white py-2 rounded mt-2 hover:bg-blue-700">
            {isLogin ? 'Увійти' : 'Зареєструватись'}
          </button>
        </form>

        <p className="text-center mt-4 text-sm">
          {isLogin ? 'Немає акаунту? ' : 'Вже зареєстровані? '}
          <span 
            className="text-blue-500 cursor-pointer hover:underline"
            onClick={() => setIsLogin(!isLogin)}
          >
            {isLogin ? 'Створити' : 'Увійти'}
          </span>
        </p>
      </div>
    </div>
  );
}