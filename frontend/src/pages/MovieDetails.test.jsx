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
  content_id: '11111111-1111-4111-8111-111111111111',
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

const user = { user_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', nickname: 'viewer' };

const renderDetails = (props = {}) =>
  render(
    <MovieDetails
      movie={mockMovie}
      user={user}
      isLoggedIn
      isWatched
      openAuth={vi.fn()}
      onBack={() => {}}
      onToggleWatched={vi.fn()}
      {...props}
    />
  );

describe('MovieDetails review form (FR-003, FR-004)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue({ data: { items: [] } });
    apiClient.post.mockResolvedValue({
      data: { review_id: 'r1', user_id: user.user_id, content_id: mockMovie.content_id, rating: 10, review_text: null },
    });
  });

  it('asks a guest to log in instead of showing the form', async () => {
    // Trace: T-006
    const openAuth = vi.fn();
    renderDetails({ isLoggedIn: false, user: null, isWatched: false, openAuth });

    await userEvent.click(screen.getByRole('button', { name: 'Увійти / Зареєструватися' }));

    expect(openAuth).toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Поставити оцінку' })).not.toBeInTheDocument();
  });

  it('offers to mark the title as watched before rating it', async () => {
    // Trace: T-035
    const onToggleWatched = vi.fn();
    renderDetails({ isWatched: false, onToggleWatched });

    expect(screen.getByText(/після того, як ви позначите його як переглянутий/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Поставити оцінку' })).not.toBeInTheDocument();

    const buttons = screen.getAllByRole('button', { name: /Позначити як переглянуте/ });
    await userEvent.click(buttons[buttons.length - 1]);
    expect(onToggleWatched).toHaveBeenCalledWith(mockMovie.content_id);
  });

  it('lets a user rate a watched title without sending a user id', async () => {
    // Trace: T-005
    renderDetails();

    await userEvent.click(await screen.findByRole('button', { name: 'Поставити оцінку' }));

    expect(apiClient.post).toHaveBeenCalledWith('/reviews', {
      content_id: mockMovie.content_id,
      rating: 10,
      review_text: null,
      contains_spoilers: false,
    });
  });

  it('explains the error when the server says the title is not watched', async () => {
    // Trace: T-035
    apiClient.post.mockRejectedValue({
      response: { status: 403, data: { error: { code: 'CONTENT_NOT_WATCHED' } } },
    });
    renderDetails();

    await userEvent.click(await screen.findByRole('button', { name: 'Поставити оцінку' }));

    expect(await screen.findByText('Спершу позначте фільм як переглянутий, щоб оцінити його.')).toBeInTheDocument();
  });

  it('opens the login window when the session has expired', async () => {
    // Trace: T-006
    apiClient.post.mockRejectedValue({ response: { status: 401, data: { error: { code: 'INVALID_TOKEN' } } } });
    const openAuth = vi.fn();
    renderDetails({ openAuth });

    await userEvent.click(await screen.findByRole('button', { name: 'Поставити оцінку' }));

    expect(await screen.findByText('Сесія завершилась. Увійдіть ще раз.')).toBeInTheDocument();
    expect(openAuth).toHaveBeenCalled();
  });

  it('shows my existing rating instead of the form', async () => {
    // Trace: T-005
    apiClient.get.mockResolvedValue({
      data: { items: [{ review_id: 'r1', user_id: user.user_id, content_id: mockMovie.content_id, rating: 7, review_text: null }] },
    });
    renderDetails();

    expect(await screen.findByText('★ 7/10', { selector: 'b' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Поставити оцінку' })).not.toBeInTheDocument();
  });

  it('shows the nickname of each review author', async () => {
    // Trace: T-038
    apiClient.get.mockResolvedValue({
      data: { items: [{ review_id: 'r9', user_id: 'other', author_nickname: 'olena', content_id: mockMovie.content_id, rating: 8, review_text: 'Дуже атмосферно і красиво' }] },
    });
    renderDetails();

    expect(await screen.findByText('olena')).toBeInTheDocument();
    expect(screen.queryByText('Глядач')).not.toBeInTheDocument();
  });

  it('does not offer rating for titles outside the catalog', () => {
    // Trace: T-035
    renderDetails({ movie: { ...mockMovie, content_id: undefined } });

    expect(screen.getByText('Оцінювати можна лише фільми з каталогу.')).toBeInTheDocument();
  });
});
