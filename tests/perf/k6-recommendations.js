import http from 'k6/http';
import { check, sleep } from 'k6';

// k6 load test script for T-022 (FR-007, NFR PERF-001)
// Target: 100 virtual users (VUs), p95 response time < 500ms, error rate < 1%
// Run: k6 run -e API_URL=http://localhost:8000 -e USER_EMAIL=... -e USER_PASSWORD=... tests/perf/k6-recommendations.js
// (e.g. the SEED_USER_EMAIL / SEED_USER_PASSWORD account from .env)

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
const EMAIL = __ENV.USER_EMAIL;
const PASSWORD = __ENV.USER_PASSWORD;

// Log in once; recommendations are always built for the user from the access token
export function setup() {
  if (!EMAIL || !PASSWORD) {
    throw new Error('Set USER_EMAIL and USER_PASSWORD (-e USER_EMAIL=... -e USER_PASSWORD=...)');
  }
  const res = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify({ email: EMAIL, password: PASSWORD }), {
    headers: { 'Content-Type': 'application/json' },
  });
  check(res, { 'login succeeded': (r) => r.status === 200 });
  return { token: JSON.parse(res.body).access_token };
}

export default function (data) {
  const res = http.get(`${BASE_URL}/api/v1/recommendations?limit=10`, {
    headers: { Authorization: `Bearer ${data.token}` },
  });
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
