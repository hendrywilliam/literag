import http from 'k6/http';

import { BASE_URL, READ_TIMEOUT } from '../config.js';

const JSON_HEADERS = {
  'Content-Type': 'application/json',
};

// `http.expectedStatuses` needs k6 >= 0.53. Guard so the suite still loads on
// older builds, where a 4xx response would otherwise count as a failure.
const EXPECT_200 =
  typeof http.expectedStatuses === 'function' ? http.expectedStatuses(200) : undefined;

/**
 * Shared HTTP helpers for the backend API.
 *
 * `profile` is the traffic tag ('read' or 'write'), not the endpoint name: it is
 * what the thresholds key off, so it must match the `scenario` tag in
 * `config.js`.
 */
export function getJson(path, { endpoint, profile = 'read' } = {}) {
  return http.get(`${BASE_URL}${path}`, {
    tags: { scenario: profile, endpoint },
    timeout: READ_TIMEOUT,
    responseCallback: EXPECT_200,
  });
}

export function postJson(path, body, { endpoint, profile = 'write' } = {}) {
  return http.post(`${BASE_URL}${path}`, JSON.stringify(body), {
    headers: JSON_HEADERS,
    tags: { scenario: profile, endpoint },
    timeout: READ_TIMEOUT,
    responseCallback: EXPECT_200,
  });
}
