// @vitest-environment node
// Reliability, finding 14 (fault injection): one automatic repeat of reading requests.
// Faults injected: the first request hangs (sleeping hosting), answers 503, or the server keeps failing.
// Chosen reaction: a GET/HEAD is repeated once after a pause; a request that changes data is never repeated,
// and after the single repeat the error reaches the page ("the server is not responding").
import http from 'node:http';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import apiClient, { RETRY_DELAY_MS, shouldRetry } from '../api/client';

let server;
let baseUrl;
let script = [];
let hits = 0;

beforeAll(async () => {
  server = http.createServer((request, response) => {
    hits += 1;
    const step = script.shift() || 'ok';
    if (step === 'hang') return; // never answer
    if (step === 'unavailable') {
      response.writeHead(503).end();
      return;
    }
    response.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify({ items: [] }));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

afterEach(() => {
  script = [];
  hits = 0;
  server.closeAllConnections();
});

afterAll(async () => {
  await new Promise(resolve => server.close(resolve));
});

const fast = { timeout: 200, retryDelayMs: 10 };

describe('one repeat of reading requests (reliability, finding 14)', () => {
  it('a GET that timed out once succeeds on the repeat', async () => {
    script = ['hang', 'ok'];

    const response = await apiClient.get(`${baseUrl}/api/v1/movies`, fast);

    expect(response.status).toBe(200);
    expect(hits).toBe(2);
  });

  it('a GET answered with 503 is repeated', async () => {
    script = ['unavailable', 'ok'];

    const response = await apiClient.get(`${baseUrl}/api/v1/movies`, fast);

    expect(response.status).toBe(200);
    expect(hits).toBe(2);
  });

  it('gives up after exactly one repeat', async () => {
    script = ['unavailable', 'unavailable', 'unavailable'];

    const error = await apiClient.get(`${baseUrl}/api/v1/movies`, fast).catch(err => err);

    expect(error.response.status).toBe(503);
    expect(hits).toBe(2);
  });

  it('never repeats a request that changes data', async () => {
    script = ['unavailable', 'ok'];

    const error = await apiClient.post(`${baseUrl}/api/v1/reviews`, { rating: 9 }, fast).catch(err => err);

    expect(error.response.status).toBe(503);
    expect(hits).toBe(1);
  });
});

describe('which failures are repeated', () => {
  const failure = (method, extra) => ({ config: { method }, ...extra });

  it('repeats only reading requests after a timeout, a network error or 502/503/504', () => {
    expect(RETRY_DELAY_MS).toBe(1000);
    expect(shouldRetry(failure('get', { code: 'ECONNABORTED' }))).toBe(true);
    expect(shouldRetry(failure('head', { code: 'ERR_NETWORK' }))).toBe(true);
    expect(shouldRetry(failure('get', { response: { status: 504 } }))).toBe(true);
    // Client errors and data changes are not repeated, nor a request that was already repeated
    expect(shouldRetry(failure('get', { response: { status: 404 } }))).toBe(false);
    expect(shouldRetry(failure('get', { response: { status: 500 } }))).toBe(false);
    expect(shouldRetry(failure('delete', { code: 'ECONNABORTED' }))).toBe(false);
    expect(shouldRetry({ config: { method: 'get', retried: true }, code: 'ECONNABORTED' })).toBe(false);
    expect(shouldRetry({ code: 'ECONNABORTED' })).toBe(false);
  });
});
