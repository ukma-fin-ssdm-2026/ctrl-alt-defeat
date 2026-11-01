import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import MovieDetails from './MovieDetails';

vi.mock('../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

const movie = {
  id: 1,
  content_id: '11111111-1111-4111-8111-111111111111',
  title: 'Дюна',
  title_en: 'Dune',
  genre: 'Фантастика',
  year: 2024,
  rating: 8.8,
};
const user = { user_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', nickname: 'viewer' };

const renderDetails = (props = {}) =>
  render(
    <MovieDetails
      movie={movie}
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
      data: { review_id: 'r1', user_id: user.user_id, content_id: movie.content_id, rating: 10, review_text: null },
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
    expect(onToggleWatched).toHaveBeenCalledWith(movie.content_id);
  });

  it('lets a user rate a watched title without sending a user id', async () => {
    // Trace: T-005
    renderDetails();

    await userEvent.click(await screen.findByRole('button', { name: 'Поставити оцінку' }));

    expect(apiClient.post).toHaveBeenCalledWith('/reviews', {
      content_id: movie.content_id,
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
      data: { items: [{ review_id: 'r1', user_id: user.user_id, content_id: movie.content_id, rating: 7, review_text: null }] },
    });
    renderDetails();

    expect(await screen.findByText('★ 7/10', { selector: 'b' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Поставити оцінку' })).not.toBeInTheDocument();
  });

  it('does not offer rating for titles outside the catalog', () => {
    // Trace: T-035
    renderDetails({ movie: { ...movie, content_id: undefined } });

    expect(screen.getByText('Оцінювати можна лише фільми з каталогу.')).toBeInTheDocument();
  });
});
