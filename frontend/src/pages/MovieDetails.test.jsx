import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import MovieDetails from './MovieDetails';

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockMovie = {
  id: 1,
  content_id: '11111111-1111-1111-1111-111111111111',
  title: 'Дюна',
  title_en: 'Dune',
  genre: 'Фантастика',
  year: 2024,
  rating: 8.5,
  img: 'https://example.com/dune.jpg',
  description: 'Фантастичний епос',
};

const authorUserId = '22222222-2222-2222-2222-222222222222';
const otherUserId = '33333333-3333-3333-3333-333333333333';
const adminUserId = '99999999-9999-9999-9999-999999999999';

const mockReview = {
  review_id: '44444444-4444-4444-4444-444444444444',
  user_id: authorUserId,
  author: 'AuthorUser',
  rating: 9,
  review_text: 'Неймовірний візуальний шедевр!',
  created_at: '2026-10-31T12:00:00Z',
  likes: 5,
};

describe('MovieDetails Review Deletion (FR-008, US-006)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue({ data: { items: [mockReview] } });
  });

  it('does not show delete button for guest users', async () => {
    render(
      <MovieDetails
        movie={mockMovie}
        user={null}
        isLoggedIn={false}
        openAuth={vi.fn()}
        onBack={vi.fn()}
      />
    );

    expect(await screen.findByText('Неймовірний візуальний шедевр!')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Видалити/ })).not.toBeInTheDocument();
  });

  it('does not show delete button for another regular user (BOLA protection)', async () => {
    const regularUser = { user_id: otherUserId, role: 'user', nickname: 'OtherUser' };

    render(
      <MovieDetails
        movie={mockMovie}
        user={regularUser}
        isLoggedIn={true}
        openAuth={vi.fn()}
        onBack={vi.fn()}
      />
    );

    expect(await screen.findByText('Неймовірний візуальний шедевр!')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Видалити/ })).not.toBeInTheDocument();
  });

  it('shows delete button for the author of the review', async () => {
    const author = { user_id: authorUserId, role: 'user', nickname: 'AuthorUser' };

    render(
      <MovieDetails
        movie={mockMovie}
        user={author}
        isLoggedIn={true}
        openAuth={vi.fn()}
        onBack={vi.fn()}
      />
    );

    const deleteBtn = await screen.findByRole('button', { name: /Видалити/ });
    expect(deleteBtn).toBeInTheDocument();
    expect(screen.queryByText('адмін')).not.toBeInTheDocument();
  });

  it('shows delete button with admin badge for administrators', async () => {
    const admin = { user_id: adminUserId, role: 'admin', nickname: 'Admin' };

    render(
      <MovieDetails
        movie={mockMovie}
        user={admin}
        isLoggedIn={true}
        openAuth={vi.fn()}
        onBack={vi.fn()}
      />
    );

    const deleteBtn = await screen.findByRole('button', { name: /Видалити/ });
    expect(deleteBtn).toBeInTheDocument();
    expect(screen.getByText('адмін')).toBeInTheDocument();
  });

  it('prompts confirmation and deletes review on confirm for admin', async () => {
    const admin = { user_id: adminUserId, role: 'admin', nickname: 'Admin' };
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    apiClient.delete.mockResolvedValueOnce({ status: 204 });

    render(
      <MovieDetails
        movie={mockMovie}
        user={admin}
        isLoggedIn={true}
        openAuth={vi.fn()}
        onBack={vi.fn()}
      />
    );

    const deleteBtn = await screen.findByRole('button', { name: /Видалити/ });
    await userEvent.click(deleteBtn);

    expect(confirmSpy).toHaveBeenCalled();
    expect(apiClient.delete).toHaveBeenCalledWith(`/reviews/${mockReview.review_id}`);

    await waitFor(() => {
      expect(screen.queryByText('Неймовірний візуальний шедевр!')).not.toBeInTheDocument();
    });

    confirmSpy.mockRestore();
  });

  it('cancels deletion if user rejects confirmation dialog', async () => {
    const admin = { user_id: adminUserId, role: 'admin', nickname: 'Admin' };
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

    render(
      <MovieDetails
        movie={mockMovie}
        user={admin}
        isLoggedIn={true}
        openAuth={vi.fn()}
        onBack={vi.fn()}
      />
    );

    const deleteBtn = await screen.findByRole('button', { name: /Видалити/ });
    await userEvent.click(deleteBtn);

    expect(confirmSpy).toHaveBeenCalled();
    expect(apiClient.delete).not.toHaveBeenCalled();
    expect(screen.getByText('Неймовірний візуальний шедевр!')).toBeInTheDocument();

    confirmSpy.mockRestore();
  });
});

