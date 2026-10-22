import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import ReviewsPage from './pages/ReviewsPage';

export default function App() {
  return (
    <Router>
      {}
      <header style={{ padding: '1rem', borderBottom: '1px solid #444', marginBottom: '1rem' }}>
        <nav style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <Link to="/" style={{ textDecoration: 'none', color: '#646cff', fontSize: '18px' }}>Головна</Link>
          <Link to="/reviews" style={{ textDecoration: 'none', color: '#646cff', fontSize: '18px' }}>Відгуки</Link>
        </nav>
      </header>

      {}
      <main style={{ padding: '0 1rem', maxWidth: '800px', margin: '0 auto' }}>
        <Routes>
          <Route path="/" element={<h1 style={{ textAlign: 'center' }}>Головна сторінка проєкту</h1>} />
          <Route path="/reviews" element={<ReviewsPage />} />
        </Routes>
      </main>
    </Router>
  );
}