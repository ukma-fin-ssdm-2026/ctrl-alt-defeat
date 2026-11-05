import { describe, expect, it } from 'vitest';
import { applyVote, nextVote } from './reviewVotes';

describe('review votes', () => {
  it('toggles and switches the vote', () => {
    expect(nextVote(0, 1)).toBe(1);
    expect(nextVote(1, 1)).toBe(0);
    expect(nextVote(1, -1)).toBe(-1);
    expect(nextVote(-1, -1)).toBe(0);
  });

  it('moves one vote between the counters', () => {
    expect(applyVote({ likes: 2, dislikes: 1 }, 0, 1)).toEqual({ likes: 3, dislikes: 1 });
    expect(applyVote({ likes: 3, dislikes: 1 }, 1, -1)).toEqual({ likes: 2, dislikes: 2 });
    expect(applyVote({ likes: 2, dislikes: 2 }, -1, 0)).toEqual({ likes: 2, dislikes: 1 });
    expect(applyVote({}, 0, -1)).toEqual({ likes: 0, dislikes: 1 });
    expect(applyVote({ likes: 0, dislikes: 0 }, 1, 0)).toEqual({ likes: 0, dislikes: 0 });
  });
});
