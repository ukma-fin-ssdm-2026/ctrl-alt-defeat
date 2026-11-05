import { useEffect, useState, useSyncExternalStore } from 'react';
import { computeAchievements } from '../utils/achievements';
import { activityXp, reachedRanks } from '../utils/ranks';

// A reached rank is announced like a badge (kind: 'rank', id 'rank-<rank id>')
const rankBadge = rank => ({
  kind: 'rank',
  id: `rank-${rank.id}`,
  icon: rank.icon,
  titleUkr: rank.titleUkr,
  titleEn: rank.titleEn,
  descUkr: `Ви отримали ранг «${rank.titleUkr}» (від ${rank.minXp} XP)`,
  descEn: `You reached the "${rank.titleEn}" rank (${rank.minXp}+ XP)`,
});

const storageKey = userId => `achievements-seen:${userId}`;

// Browser storage can be unavailable (private mode, blocked site data): then nothing is remembered
function readSeen(userId) {
  try {
    const raw = window.localStorage.getItem(storageKey(userId));
    return raw ? new Set(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

function writeSeen(userId, ids) {
  try {
    window.localStorage.setItem(storageKey(userId), JSON.stringify([...ids]));
  } catch {
    // ignore: notifications just may repeat in this browser
  }
}

// Queue of badges waiting to be shown. It lives outside React state so the effect below
// only talks to an external system (storage + this queue) and the UI subscribes to it.
function createQueue() {
  let snapshot = { userId: null, items: [] };
  const listeners = new Set();
  const set = next => {
    snapshot = next;
    listeners.forEach(listener => listener());
  };
  return {
    subscribe: listener => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    get: () => snapshot,
    push: (userId, badges) => set({
      userId,
      items: [...(snapshot.userId === userId ? snapshot.items : []), ...badges],
    }),
    shift: () => set({ ...snapshot, items: snapshot.items.slice(1) }),
  };
}

// Watches the user's activity and returns newly unlocked achievements and ranks one by one.
// Badges the user already had when this browser first saw the account are not announced,
// and a badge is announced only once even if it is lost and earned again.
export default function useAchievementNotifications({ user, reviews, watched, watchlist, ready, now }) {
  const userId = user?.user_id ?? null;
  const createdAt = user?.created_at;
  const [queue] = useState(createQueue);
  const snapshot = useSyncExternalStore(queue.subscribe, queue.get);

  useEffect(() => {
    if (!userId || !ready) return;
    const unlocked = [
      ...computeAchievements({ reviews, watched, watchlist, createdAt, now: now ?? Date.now() })
        .filter(badge => badge.unlocked),
      ...reachedRanks(activityXp({ reviews, watched, watchlist })).map(rankBadge),
    ];
    const seen = readSeen(userId);
    if (!seen) {
      // First visit of this account in this browser: remember the current state silently
      writeSeen(userId, unlocked.map(badge => badge.id));
      return;
    }
    const fresh = unlocked.filter(badge => !seen.has(badge.id));
    if (fresh.length === 0) return;
    fresh.forEach(badge => seen.add(badge.id));
    writeSeen(userId, seen);
    queue.push(userId, fresh);
  }, [queue, userId, ready, reviews, watched, watchlist, createdAt, now]);

  const items = snapshot.userId === userId ? snapshot.items : [];
  return { current: items[0] || null, pending: Math.max(0, items.length - 1), dismiss: queue.shift };
}
