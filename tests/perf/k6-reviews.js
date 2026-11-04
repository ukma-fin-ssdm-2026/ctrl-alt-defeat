import http from 'k6/http';
import { check, sleep } from 'k6';

// k6 load test script for T-025 (US-008, NFR PERF-001): guests browsing a movie page
// (reviews list + audience rating). Target: 100 VUs, p95 < 500 ms, errors < 1%.
// Run: k6 run -e API_URL=http://localhost:8000 tests/perf/k6-reviews.js

export const options = {
  stages: [
    { duration: '1m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '1m', target: 100 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

export function setup() {
  const res = http.get(`${BASE_URL}/api/v1/movies?limit=20`);
  return { ids: JSON.parse(res.body).items.map((movie) => movie.content_id) };
}

export default function (data) {
  const contentId = data.ids[Math.floor(Math.random() * data.ids.length)];

  const reviews = http.get(`${BASE_URL}/api/v1/reviews?content_id=${contentId}&limit=10`);
  check(reviews, { 'reviews 200': (r) => r.status === 200 });

  const summary = http.get(`${BASE_URL}/api/v1/reviews/summary?content_id=${contentId}`);
  check(summary, {
    'summary 200': (r) => r.status === 200,
    'summary has count': (r) => typeof JSON.parse(r.body).ratings_count === 'number',
  });

  sleep(1);
}
