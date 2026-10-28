import { useState } from 'react';
import apiClient from '../api/client';

export default function ReviewForm({ onReviewAdded }) {
  const [rating, setRating] = useState(10);
  const [reviewText, setReviewText] = useState('');
  const [containsSpoilers, setContainsSpoilers] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    const newReview = {
      user_id: "550e8400-e29b-41d4-a716-446655440000",
      content_id: "550e8400-e29b-41d4-a716-446655440001",
      rating: Number.parseInt(rating, 10),
      review_text: reviewText,
      contains_spoilers: containsSpoilers
    };

    apiClient.post('/api/v1/reviews', newReview)
      .then(() => {
        setReviewText('');
        setRating(10);
        setContainsSpoilers(false);
        if (onReviewAdded) onReviewAdded();
      })
      .catch(error => console.error('Помилка:', error));
  };

  return (
  <form onSubmit={handleSubmit} style={{ border: '1px solid #646cff', padding: '20px', marginBottom: '30px', borderRadius: '8px' }}>
    <h3 style={{ marginTop: 0 }}>Написати відгук</h3>
    
    <div style={{ marginBottom: '15px' }}>
      <label htmlFor="rating-input" style={{ display: 'block', marginBottom: '5px' }}>
        Оцінка (1-10):
      </label>
      <input 
        id="rating-input"
        type="number" 
        min="1" 
        max="10" 
        value={rating} 
        onChange={e => setRating(e.target.value)} 
        required 
        style={{ width: '100%' }} 
      />
    </div>

    <div style={{ marginBottom: '15px' }}>
      <label htmlFor="review-text-input" style={{ display: 'block', marginBottom: '5px' }}>
        Текст відгуку:
      </label>
      <textarea 
        id="review-text-input"
        value={reviewText} 
        onChange={e => setReviewText(e.target.value)} 
        required 
        minLength="10" 
        style={{ width: '100%', minHeight: '80px' }} 
      />
    </div>

    <div style={{ marginBottom: '15px' }}>
      <label htmlFor="spoilers-checkbox">
        <input 
          id="spoilers-checkbox"
          type="checkbox" 
          checked={containsSpoilers} 
          onChange={e => setContainsSpoilers(e.target.checked)} 
        />
        {' '}Містить спойлери
      </label>
    </div>

    <button type="submit" style={{ cursor: 'pointer' }}>Відправити</button>
  </form>
);
