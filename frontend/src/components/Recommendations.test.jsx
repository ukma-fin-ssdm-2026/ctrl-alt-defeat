import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import { CURRENT_USER_ID } from '../auth/currentUser';
import Recommendations from './Recommendations';

vi.mock('../api/client', () => ({
  default: { get: vi.fn() },
}));

const items = [
  { id: 2, content_id: 'c2', title: 'Interstellar', genre: 'Фантастика', category: 'Movie', rating: 8.7, year: 2014 },
  { id: 9, content_id: 'c9', title: 'Alien', genre: 'Фантастика', category: 'Movie', rating: 8.5, year: 1979 },
  { id: 3, content_id: 'c3', title: 'Blade Runner 2049', genre: 'Фантастика', category: 'Movie', rating: 8.0, year: 2017 },
  { id: 4, content_id: 'c4', title: 'Shawshank', genre: 'Драма', category: 'Movie', rating: 9.3, year: 1994 },
  { id: 5, content_id: 'c5', title: 'Forrest Gump', genre: 'Драма', category: 'Movie', rating: 8.8, year: 1994 },
];

describe('Recommendations block (FR-007)', () => {
  beforeEach(() => {
    apiClient.get.mockReset();
  });

  it('requests recommendations for the current user and shows at least five titles', async () => {
    // Trace: T-020
    apiClient.get.mockResolvedValue({ data: { items, personalized: true, favorite_genres: ['Фантастика'] } });

    render(<Recommendations isLoggedIn onSelectMovie={() => {}} />);

    expect(screen.getByText('Рекомендовано для вас')).toBeInTheDocument();
    expect(await screen.findByText('Interstellar')).toBeInTheDocument();
    items.forEach(movie => expect(screen.getByText(movie.title)).toBeInTheDocument());
    expect(apiClient.get).toHaveBeenCalledWith('/recommendations', {
      params: { user_id: CURRENT_USER_ID, limit: 10 },
    });
  });

  it('explains which genres the recommendations are based on', async () => {
    // Trace: T-020
    apiClient.get.mockResolvedValue({ data: { items, personalized: true, favorite_genres: ['Фантастика', 'Драма'] } });

    render(<Recommendations isLoggedIn onSelectMovie={() => {}} />);

    expect(await screen.findByText('На основі ваших улюблених жанрів: Фантастика, Драма')).toBeInTheDocument();
  });

  it('tells a new user that the picks are not personal yet', async () => {
    // Trace: T-020
    apiClient.get.mockResolvedValue({ data: { items, personalized: false, favorite_genres: [] } });

    render(<Recommendations isLoggedIn onSelectMovie={() => {}} />);

    expect(await screen.findByText(/Найкраще з каталогу/)).toBeInTheDocument();
  });

  it('opens a movie when a recommendation is clicked', async () => {
    // Trace: T-020
    apiClient.get.mockResolvedValue({ data: { items, personalized: true, favorite_genres: ['Фантастика'] } });
    const onSelectMovie = vi.fn();

    render(<Recommendations isLoggedIn onSelectMovie={onSelectMovie} />);
    await userEvent.click(await screen.findByText('Alien'));

    expect(onSelectMovie).toHaveBeenCalledWith(items[1]);
  });

  it('asks a guest to log in and does not call the API', async () => {
    // Trace: T-021
    const openAuth = vi.fn();

    render(<Recommendations isLoggedIn={false} openAuth={openAuth} onSelectMovie={() => {}} />);
    await userEvent.click(screen.getByRole('button', { name: 'Увійти' }));

    expect(openAuth).toHaveBeenCalledTimes(1);
    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it('hides the block when the backend is unavailable', async () => {
    // Trace: T-020
    apiClient.get.mockRejectedValue(new Error('Network Error'));
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    const { container } = render(<Recommendations isLoggedIn onSelectMovie={() => {}} />);

    await vi.waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
