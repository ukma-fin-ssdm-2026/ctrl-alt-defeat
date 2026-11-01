// Strict UUID check for ids that are sent to the API (defense in depth for request data).

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const isUuid = value => typeof value === 'string' && UUID_PATTERN.test(value);
