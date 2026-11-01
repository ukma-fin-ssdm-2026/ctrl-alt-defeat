import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import UserProfile from './UserProfile';

vi.mock('../api/client', () => ({ default: { get: vi.fn() } }));

const user = { user_id: 'u-1', nickname: 'cinema_fan', email: 'user@example.com' };
const renderProfile = () =>
  render(<UserProfile user={user} language="UKR" watchlistMovies={[]} onSelectMovie={() => {}} onToggleWatchlist={() => {}} />);
const openReviewsTab = () => userEvent.click(screen.getByRole('button', { name: /Мої відгуки/ }));

describe('UserProfile', () => {
  beforeEach(() => {
    apiClient.get.mockReset();
  });

  it('shows the nickname of the user', () => {
    // Trace: T-037
    apiClient.get.mockResolvedValue({ data: { items: [] } });
    renderProfile();

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('cinema_fan');
  });

  it('lists my real reviews from the API', async () => {
    // Trace: T-038
    apiClient.get.mockResolvedValue({
      data: {
        items: [
          { review_id: 'r1', content_title: 'Дюна: Частина друга', rating: 9, review_text: 'Неймовірна атмосфера!', created_at: '2026-11-01T10:00:00Z' },
          { review_id: 'r2', content_title: 'Шрек', rating: 7, review_text: null, created_at: '2026-11-01T11:00:00Z' },
        ],
      },
    });
    renderProfile();
    await openReviewsTab();

    expect(apiClient.get).toHaveBeenCalledWith('/reviews', { params: { user_id: 'u-1', limit: 100 } });
    expect(await screen.findByText('Дюна: Частина друга')).toBeInTheDocument();
    expect(screen.getByText('"Неймовірна атмосфера!"')).toBeInTheDocument();
    expect(screen.getByText('Лише оцінка, без тексту')).toBeInTheDocument();
    expect(screen.queryByText(/Interstellar/)).not.toBeInTheDocument();
  });

  it('shows an empty state when I have no reviews', async () => {
    // Trace: T-038
    apiClient.get.mockResolvedValue({ data: { items: [] } });
    renderProfile();
    await openReviewsTab();

    expect(await screen.findByText('Ви ще не залишили жодної рецензії.')).toBeInTheDocument();
  });
});
