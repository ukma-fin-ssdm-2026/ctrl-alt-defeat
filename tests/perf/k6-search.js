import http from 'k6/http';
import { check, sleep } from 'k6';

// k6 load test script for T-008 (NFR PERF-001)
// Target: 100 virtual users (VUs), p95 response time < 500ms, error rate < 1%

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // Warm-up ramp-up
    { duration: '2m', target: 100 },  // Peak load: 100 concurrent users
    { duration: '1m', target: 100 },  // Sustained load
    { duration: '1m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    // PERF-001: 95th percentile response time must not exceed 500 ms
    http_req_duration: ['p(95)<500'],
    // Error rate must be strictly under 1%
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

export default function () {
  // 1. Browse reviews list with pagination
  const res1 = http.get(`${BASE_URL}/api/v1/reviews?skip=0&limit=10`);
  check(res1, {
    'status is 200': (r) => r.status === 200,
    'has valid json': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.items);
      } catch (_) {
        return false;
      }
    },
  });

  sleep(0.5);

  // 2. Filter reviews by minimum rating
  const res2 = http.get(`${BASE_URL}/api/v1/reviews?min_rating=7&limit=5`);
  check(res2, {
    'status is 200 on filtered query': (r) => r.status === 200,
  });

  sleep(0.5);
}

