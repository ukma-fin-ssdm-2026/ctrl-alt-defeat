import { useState, useEffect } from 'react';
import apiClient from '../api/client';
import ReviewCard from '../components/ReviewCard';
import ReviewForm from '../components/ReviewForm';

export default function ReviewsPage() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchReviews = () => {
    setLoading(true);
    apiClient.get('/reviews')
      .then(response => {
        setReviews(response.data.items || []);
        setLoading(false);
      })
      .catch(error => {
        if (error.response && error.response.status === 422) {
          console.error('Помилка валідації від FastAPI:', error.response.data.detail);
        } else {
          console.error('Помилка відправки:', error);
        }
      });
  };

  useEffect(() => {
    fetchReviews();
  }, []);

  return (
    <div>
      <h1 style={{ textAlign: 'center' }}>Відгуки</h1>
      
      <ReviewForm onReviewAdded={fetchReviews} />
      
      {loading ? (
        <p>Завантаження відгуків...</p>
      ) : reviews.length === 0 ? (
        <p style={{ textAlign: 'center' }}>Немає доступних відгуків. Будьте першим!</p>
      ) : (
        <div>
          {reviews.map((review) => (
            <ReviewCard key={review.review_id} review={review} />
          ))}
        </div>
      )}
    </div>
  );
}