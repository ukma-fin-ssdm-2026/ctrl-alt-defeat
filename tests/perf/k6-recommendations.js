import http from 'k6/http';
import { check, sleep } from 'k6';

// k6 load test script for T-022 (FR-007, NFR PERF-001)
// Target: 100 virtual users (VUs), p95 response time < 500ms, error rate < 1%
// Run: k6 run -e API_URL=http://localhost:8000 tests/perf/k6-recommendations.js

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // Warm-up ramp-up
    { duration: '2m', target: 100 },  // Peak load: 100 concurrent users
    { duration: '1m', target: 100 },  // Sustained load
    { duration: '1m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';
// Temporary until authentication (FR-001): recommendations are requested for a user id
const USER_ID = __ENV.USER_ID || '3fa85f64-5717-4562-b3fc-2c963f66afa6';

export default function () {
  const res = http.get(`${BASE_URL}/api/v1/recommendations?user_id=${USER_ID}&limit=10`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'has recommendations': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.items) && typeof body.personalized === 'boolean';
      } catch (_) {
        return false;
      }
    },
  });

  sleep(1);
}
