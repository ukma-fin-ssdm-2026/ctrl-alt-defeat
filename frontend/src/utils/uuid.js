// Safe builders for API paths that contain ids (prevents path traversal / request forgery).

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const isUuid = value => typeof value === 'string' && UUID_PATTERN.test(value);

export function reviewCommentsPath(reviewId) {
  if (!isUuid(reviewId)) {
    throw new Error(`Invalid review id: ${String(reviewId).slice(0, 40)}`);
  }
  return `/reviews/${encodeURIComponent(reviewId)}/comments`;
}
