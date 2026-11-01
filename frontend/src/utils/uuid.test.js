import { describe, expect, it } from 'vitest';
import { isUuid, reviewCommentsPath } from './apiPaths';

const ID = '11111111-1111-4111-8111-111111111111';

describe('apiPaths', () => {
  it('builds the comments path for a valid review id', () => {
    expect(reviewCommentsPath(ID)).toBe(`/reviews/${ID}/comments`);
  });

  it.each(['../../admin', `${ID}/../../users`, `${ID}?x=1`, '', null, undefined, 42])(
    'rejects an unsafe review id: %s',
    value => {
      expect(isUuid(value)).toBe(false);
      expect(() => reviewCommentsPath(value)).toThrow('Invalid review id');
    }
  );
});
