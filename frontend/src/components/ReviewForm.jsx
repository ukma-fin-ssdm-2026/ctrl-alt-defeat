import { useState } from 'react';
import apiClient from '../api/client';

export default function ReviewForm({ contentId, onReviewAdded }) {
  const [rating, setRating] = useState(10);
  const [reviewText, setReviewText] = useState('');
  const [containsSpoilers, setContainsSpoilers] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSubmitting(true);
    
    const newReview = {
      content_id: contentId || "550e8400-e29b-41d4-a716-446655440001",
      rating: Number.parseInt(rating, 10),
      review_text: reviewText,
      contains_spoilers: containsSpoilers
    };

    apiClient.post('/reviews', newReview)
      .then(() => {
        setReviewText('');
        setRating(10);
        setContainsSpoilers(false);
        setSubmitting(false);
        if (onReviewAdded) onReviewAdded();
      })
      .catch(error => {
        console.error('Помилка відправки відгуку:', error.response?.data || error.message);
        setErrorMessage(
          error.response?.data?.message || 
          'Не вдалося надіслати відгук. Перевірте з’єднання з бекендом.'
        );
        setSubmitting(false);
      });
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
          style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #ccc' }} 
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
          style={{ width: '100%', minHeight: '80px', padding: '8px', borderRadius: '6px', border: '1px solid #ccc' }} 
        />
      </div>

      <div style={{ marginBottom: '15px' }}>
        <label htmlFor="spoilers-checkbox" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input 
            id="spoilers-checkbox"
            type="checkbox" 
            checked={containsSpoilers} 
            onChange={e => setContainsSpoilers(e.target.checked)} 
          />
          Містить спойлери
        </label>
      </div>

      {errorMessage && (
        <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#ffe6e6', color: '#d8000c', borderRadius: '6px', fontSize: '13px' }}>
          {errorMessage}
        </div>
      )}

      <button 
        type="submit" 
        disabled={submitting}
        style={{ cursor: 'pointer', padding: '10px 20px', backgroundColor: '#646cff', color: '#white', border: 'none', borderRadius: '6px', fontWeight: 'bold' }}
      >
        {submitting ? 'Відправка...' : 'Відправити'}
      </button>
    </form>
  );
}