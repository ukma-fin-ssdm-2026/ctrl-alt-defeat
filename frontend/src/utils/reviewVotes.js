// "Support" (1) / "Don't support" (-1) votes for reviews: one vote per user, 0 = no vote.

// Clicking the active button takes the vote back, the other button switches it
export function nextVote(current, clicked) {
  return current === clicked ? 0 : clicked;
}

// Counters after the user's vote changes from `from` to `to` (used for the optimistic update)
export function applyVote({ likes = 0, dislikes = 0 }, from, to) {
  const delta = value => (to === value ? 1 : 0) - (from === value ? 1 : 0);
  return {
    likes: Math.max(0, likes + delta(1)),
    dislikes: Math.max(0, dislikes + delta(-1)),
  };
}
