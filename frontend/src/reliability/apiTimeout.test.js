// @vitest-environment node
// Reliability, finding 14 (fault injection): the API client never waits forever.
// Fault injected: a server that accepts the connection and never answers. Chosen reaction: fast failure —
// the request is aborted with ECONNABORTED, and the page shows "the server is not responding".
import http from 'node:http';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import apiClient, { REQUEST_TIMEOUT_MS } from '../api/client';

let server;
let baseUrl;

beforeAll(async () => {
  server = http.createServer(() => {
    // Never answer: like a database or hosting that hangs
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

afterAll(async () => {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
});

describe('API client timeout (reliability, finding 14)', () => {
  it('has a time limit for every request', () => {
    expect(REQUEST_TIMEOUT_MS).toBe(30000);
    expect(apiClient.defaults.timeout).toBe(REQUEST_TIMEOUT_MS);
  });

  it('aborts a request to a hanging server instead of waiting forever', async () => {
    const started = Date.now();

    // A short limit and pause for the test; the mechanism is the same as with the default 30 s and 1 s.
    // A GET is repeated once (apiRetry.test.js), so the error comes after the second timeout.
    const error = await apiClient.get(`${baseUrl}/api/v1/movies`, { timeout: 200, retryDelayMs: 10 }).catch(err => err);

    expect(error.code).toBe('ECONNABORTED');
    expect(Date.now() - started).toBeLessThan(2000);
  });
});
