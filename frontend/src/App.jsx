import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ReviewsPage from './pages/ReviewsPage';

export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ padding: '1rem', borderBottom: '1px solid #ccc', marginBottom: '2rem' }}>
        <Link to="/" style={{ marginRight: '1rem' }}>Головна</Link>
        <Link to="/reviews">Відгуки</Link>
      </nav>
      
      <main style={{ padding: '0 1rem' }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/reviews" element={<ReviewsPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}