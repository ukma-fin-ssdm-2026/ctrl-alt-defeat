import { renderHook, waitFor } from '@testing-library/react';
import { expect, vi } from 'vitest';
import apiClient from '../api/client';

// Shared fixtures for hooks built on useUserList (watchlist, watched list)
export const user = { user_id: 'u-1' };
export const dune = { id: 1, content_id: '11111111-1111-4111-8111-111111111111', title: 'Dune' };
export const shrek = { id: 3, content_id: '33333333-3333-4333-8333-333333333333', title: 'Shrek' };
export const mockOnly = { id: 99, title: 'Mock movie without content id' };

export async function renderListHook(useHook, props = {}) {
  const hook = renderHook(p => useHook(p), { initialProps: { user, catalog: [dune, shrek, mockOnly], ...props } });
  const activeUser = 'user' in props ? props.user : user;
  if (activeUser) await waitFor(() => expect(apiClient.get).toHaveBeenCalled());
  return hook;
}

// Resets the mocked apiClient (vi.mock('../api/client') in the test file) with default answers
export function mockListApi({ items = [dune], created = shrek } = {}) {
  vi.clearAllMocks();
  apiClient.get.mockResolvedValue({ data: { items } });
  apiClient.post.mockResolvedValue({ data: created });
  apiClient.delete.mockResolvedValue({});
}
