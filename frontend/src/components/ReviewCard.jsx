export default function ReviewCard({ review }) {
  return (
    <div style={{ border: '1px solid #444', padding: '15px', marginBottom: '10px', borderRadius: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
        <strong>Оцінка: {review.rating}/10</strong>
        {review.contains_spoilers && <span style={{ color: '#ff4a4a', fontSize: '12px', fontWeight: 'bold' }}>Спойлери!</span>}
      </div>
      <p style={{ margin: 0 }}>{review.review_text}</p>
    </div>
  );
}