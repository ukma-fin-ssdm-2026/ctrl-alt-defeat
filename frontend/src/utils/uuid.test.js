import { describe, expect, it } from 'vitest';
import { isUuid } from './uuid';

describe('isUuid', () => {
  it('accepts a valid UUID in any case', () => {
    expect(isUuid('11111111-1111-4111-8111-111111111111')).toBe(true);
    expect(isUuid('3FA85F64-5717-4562-B3FC-2C963F66AFA6')).toBe(true);
  });

  it.each(['../../admin', '11111111-1111-4111-8111-111111111111/../users', '11111111-1111-4111-8111-111111111111?x=1', '', null, undefined, 42])(
    'rejects an unsafe value: %s',
    value => {
      expect(isUuid(value)).toBe(false);
    }
  );
});
