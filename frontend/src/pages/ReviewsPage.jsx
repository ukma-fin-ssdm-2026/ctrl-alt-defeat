import { useState, useEffect } from 'react';
import apiClient from '../api/client';

export default function ReviewsPage() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get('/api/v1/reviews') 
      .then(response => {
        setReviews(response.data.items || []);
        setLoading(false);
      })
      .catch(error => {
        console.error('Помилка завантаження відгуків:', error);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Завантаження відгуків...</p>;

  return (
    <div>
      <h1>Відгуки</h1>
      {reviews.length === 0 ? (
        <p>Немає доступних відгуків.</p>
      ) : (
        <ul>
          {reviews.map((review) => (
            <li key={review.review_id}>
              <strong>Оцінка: {review.rating}/10</strong> — {review.review_text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}