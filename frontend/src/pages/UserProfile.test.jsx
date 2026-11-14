import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import UserProfile from './UserProfile';

vi.mock('../api/client', () => ({ default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } }));

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

  it('opens the reviewed title from its poster or title, in the interface language', async () => {
    // Trace: T-038
    const review = {
      review_id: 'r1', content_id: 'c-1', content_title: 'Дюна: Частина друга', content_title_en: 'Dune: Part Two',
      content_img: '/dune.jpg', content_img_en: '/dune-en.jpg', rating: 9, review_text: 'Сильно', created_at: '2026-11-01T10:00:00Z',
    };
    const full = { id: 1, content_id: 'c-1', title: 'Дюна: Частина друга', title_en: 'Dune: Part Two', year: 2024 };
    apiClient.get.mockImplementation(url => Promise.resolve({ data: url === '/movies/c-1' ? full : { items: [review] } }));
    const onSelectMovie = vi.fn();
    render(<UserProfile user={user} language="EN" watchlistMovies={[]} onSelectMovie={onSelectMovie} onToggleWatchlist={() => {}} />);
    await userEvent.click(screen.getByRole('button', { name: /My Reviews/ }));

    // Two targets: the poster (for the mouse) and the title (also for the keyboard)
    const [posterButton, title] = await screen.findAllByRole('button', { name: 'Dune: Part Two' });
    expect(posterButton.querySelector('img')).toHaveAttribute('src', '/dune-en.jpg');
    expect(posterButton).toHaveAttribute('tabindex', '-1');
    await userEvent.click(title);
    // The full card from the catalog API opens the page
    await waitFor(() => expect(onSelectMovie).toHaveBeenCalledWith(full));
    expect(apiClient.get).toHaveBeenCalledWith('/movies/c-1');
  });

  it('opens the reviewed title with what the review knows when the catalog is unavailable', async () => {
    // Trace: T-038
    const review = { review_id: 'r1', content_id: 'c-1', content_title: 'Шрек', content_img: '/shrek.jpg', rating: 7, created_at: '2026-11-01T10:00:00Z' };
    apiClient.get.mockImplementation(url => (url === '/movies/c-1' ? Promise.reject(new Error('offline')) : Promise.resolve({ data: { items: [review] } })));
    const onSelectMovie = vi.fn();
    render(<UserProfile user={user} language="UKR" watchlistMovies={[]} onSelectMovie={onSelectMovie} onToggleWatchlist={() => {}} />);
    await openReviewsTab();

    await userEvent.click((await screen.findAllByRole('button', { name: 'Шрек' }))[1]);

    await waitFor(() => expect(onSelectMovie).toHaveBeenCalledWith(expect.objectContaining({ content_id: 'c-1', title: 'Шрек', img: '/shrek.jpg' })));
  });

  it('shows an empty state when I have no reviews', async () => {
    // Trace: T-038
    apiClient.get.mockResolvedValue({ data: { items: [] } });
    renderProfile();
    await openReviewsTab();

    expect(await screen.findByText('Ви ще не залишили жодної рецензії.')).toBeInTheDocument();
  });
});

describe('UserProfile account settings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue({ data: { items: [] } });
  });

  const fillPasswords = async (current, next, confirm = next) => {
    await userEvent.click(screen.getByRole('button', { name: /Безпека/ }));
    await userEvent.type(screen.getByLabelText('Поточний пароль'), current);
    await userEvent.type(screen.getByLabelText('Новий пароль'), next);
    await userEvent.type(screen.getByLabelText('Підтвердіть новий пароль'), confirm);
    await userEvent.click(screen.getByRole('button', { name: 'Змінити пароль' }));
  };

  it('changes the password on the server', async () => {
    apiClient.post.mockResolvedValue({ data: { message: 'Password changed' } });
    renderProfile();

    await fillPasswords('OldPass123', 'NewPass456');

    expect(apiClient.post).toHaveBeenCalledWith('/auth/change-password', { current_password: 'OldPass123', new_password: 'NewPass456' });
    expect(await screen.findByRole('status')).toHaveTextContent('Пароль успішно змінено!');
  });

  it('does not claim success when the server refuses', async () => {
    apiClient.post.mockRejectedValue({ response: { data: { error: { code: 'INVALID_PASSWORD' } } } });
    renderProfile();

    await fillPasswords('wrong', 'NewPass456');

    expect(await screen.findByRole('status')).toHaveTextContent('Поточний пароль неправильний.');
  });

  it('checks that the new passwords match before calling the server', async () => {
    renderProfile();

    await fillPasswords('OldPass123', 'NewPass456', 'Other789');

    expect(screen.getByRole('status')).toHaveTextContent('Нові паролі не збігаються!');
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('deletes the account after password confirmation', async () => {
    apiClient.delete.mockResolvedValue({ status: 204 });
    const onDeleteProfile = vi.fn();
    render(<UserProfile user={user} language="UKR" watchlistMovies={[]} onSelectMovie={() => {}} onToggleWatchlist={() => {}} onDeleteProfile={onDeleteProfile} />);

    await userEvent.click(screen.getByRole('button', { name: /Видалити акаунт/ }));
    await userEvent.type(screen.getByLabelText('Пароль для підтвердження'), 'MyPass123');
    await userEvent.click(screen.getByRole('button', { name: 'Видалити акаунт назавжди' }));

    expect(apiClient.delete).toHaveBeenCalledWith('/auth/me', { data: { password: 'MyPass123' } });
    expect(onDeleteProfile).toHaveBeenCalledTimes(1);
  });

  it('keeps the account and explains why when the server refuses', async () => {
    apiClient.delete.mockRejectedValue({ response: { data: { error: { code: 'SEED_ACCOUNT_LOCKED' } } } });
    const onDeleteProfile = vi.fn();
    render(<UserProfile user={user} language="UKR" watchlistMovies={[]} onSelectMovie={() => {}} onToggleWatchlist={() => {}} onDeleteProfile={onDeleteProfile} />);

    await userEvent.click(screen.getByRole('button', { name: /Видалити акаунт/ }));
    await userEvent.type(screen.getByLabelText('Пароль для підтвердження'), 'MyPass123');
    await userEvent.click(screen.getByRole('button', { name: 'Видалити акаунт назавжди' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Демо-акаунт не можна змінити чи видалити');
    expect(onDeleteProfile).not.toHaveBeenCalled();
  });

  it('does not offer deletion to administrators', () => {
    render(<UserProfile user={{ ...user, role: 'admin' }} language="UKR" watchlistMovies={[]} onSelectMovie={() => {}} onToggleWatchlist={() => {}} />);

    expect(screen.queryByRole('button', { name: /Видалити акаунт/ })).not.toBeInTheDocument();
  });
});

describe('UserProfile registration date', () => {
  beforeEach(() => {
    apiClient.get.mockResolvedValue({ data: { items: [] } });
  });

  it('shows the real registration date from the server', () => {
    render(<UserProfile user={{ ...user, created_at: '2026-11-05T10:30:00Z' }} language="UKR" watchlistMovies={[]} onSelectMovie={() => {}} onToggleWatchlist={() => {}} />);

    expect(screen.getByText(/5 листопада 2026/)).toBeInTheDocument();
    expect(screen.queryByText('Жовтень 2026')).not.toBeInTheDocument();
  });

  it('shows the date in English in the English interface', () => {
    render(<UserProfile user={{ ...user, created_at: '2026-11-05T10:30:00Z' }} language="EN" watchlistMovies={[]} onSelectMovie={() => {}} onToggleWatchlist={() => {}} />);

    expect(screen.getByText('5 November 2026')).toBeInTheDocument();
  });

  it('shows a dash when the date is unknown', () => {
    render(<UserProfile user={user} language="UKR" watchlistMovies={[]} onSelectMovie={() => {}} onToggleWatchlist={() => {}} />);

    expect(screen.getByText('—')).toBeInTheDocument();
  });
});

describe('UserProfile achievements', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('unlocks badges only from my real activity', async () => {
    apiClient.get.mockResolvedValue({ data: { items: [{ review_id: 'r1', rating: 8, review_text: 'Сильне кіно', created_at: '2026-11-01T10:00:00Z' }] } });
    render(
      <UserProfile
        user={{ ...user, created_at: new Date().toISOString() }}
        language="UKR"
        watchlistMovies={[{ id: 1, genres: ['Драма'] }]}
        watchedMovies={[]}
        onSelectMovie={() => {}}
        onToggleWatchlist={() => {}}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: /Нагороди/ }));

    expect(await screen.findByText('Отримано 1 з 7')).toBeInTheDocument();
    expect(screen.getByTestId('badge-first-review')).toHaveAttribute('data-unlocked', 'true');
    expect(screen.getByTestId('badge-reviewer')).toHaveAttribute('data-unlocked', 'false');
    expect(screen.getByTestId('badge-planner')).toHaveTextContent('1 / 5');
    expect(screen.queryByText('Усі медальки розблоковані!')).not.toBeInTheDocument();
  });
});

describe('UserProfile opened from an achievement pop-up', () => {
  it('opens the achievements tab and highlights the new badge', async () => {
    apiClient.get.mockResolvedValue({ data: { items: [] } });
    render(
      <UserProfile
        user={user}
        language="UKR"
        watchlistMovies={[]}
        initialTab="achievements"
        highlightAchievement="planner"
        onSelectMovie={() => {}}
        onToggleWatchlist={() => {}}
      />,
    );

    expect(await screen.findByText('Ранг і нагороди 🏆')).toBeInTheDocument();
    expect(screen.getByTestId('badge-planner')).toHaveClass('achievement-highlight');
    expect(screen.getByTestId('badge-reviewer')).not.toHaveClass('achievement-highlight');
  });
});

describe('UserProfile rank', () => {
  beforeEach(() => vi.clearAllMocks());

  const renderWith = (props = {}) => render(
    <UserProfile user={user} language="UKR" watchlistMovies={[]} watchedMovies={[]} onSelectMovie={() => {}} onToggleWatchlist={() => {}} {...props} />,
  );

  it('starts a new account as a viewer with progress to the next rank', async () => {
    apiClient.get.mockResolvedValue({ data: { items: [] } });
    renderWith();

    const chip = await screen.findByTestId('rank-chip');
    expect(chip).toHaveAttribute('data-rank', 'viewer');
    expect(chip).toHaveTextContent('Ранг: Глядач· 0 XP');
    expect(screen.getByText('До рангу «Кінолюб» ще 25 XP')).toBeInTheDocument();
  });

  it('computes the rank from real reviews and lists, and shows the ladder', async () => {
    apiClient.get.mockResolvedValue({ data: { items: [{ review_id: 'r1', rating: 9, review_text: 'Дуже сильне кіно', created_at: '2026-11-01T10:00:00Z' }] } });
    const movies = Array.from({ length: 5 }, (_, id) => ({ id, genres: ['Драма'] }));
    // 10 (review) + 5 * 3 (watched) + 5 * 1 (watchlist) = 30 XP → "Кінолюб"
    renderWith({ watchedMovies: movies, watchlistMovies: movies });

    await waitFor(() => expect(screen.getByTestId('rank-chip')).toHaveAttribute('data-rank', 'fan'));
    expect(screen.getByText('До рангу «Рецензент» ще 45 XP')).toBeInTheDocument();

    await userEvent.click(screen.getByTestId('rank-chip'));
    expect(screen.getByTestId('rank-fan')).toHaveAttribute('aria-current', 'step');
    expect(screen.getByTestId('rank-viewer')).toHaveAttribute('data-reached', 'true');
    expect(screen.getByTestId('rank-reviewer')).toHaveAttribute('data-reached', 'false');
  });
});

describe('UserProfile lists in the interface language', () => {
  const iceAge = {
    id: 7, content_id: 'c-7', title: 'Льодовиковий період: Погоня за яйцями', title_en: 'Ice Age: The Great Egg-Scapade',
    genre: 'Мультфільм', year: 2016, img: '/ice-uk.jpg', img_en: '/ice-en.jpg',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue({ data: { items: [] } });
  });

  it.each([
    ['watchlist', { initialTab: 'watchlist', watchlistMovies: [iceAge] }],
    ['watched', { initialTab: 'watched', watchlistMovies: [], watchedMovies: [iceAge] }],
  ])('shows the %s with the English title, genre and poster in English, and opens the title', async (_, props) => {
    const onSelectMovie = vi.fn();
    render(<UserProfile user={user} language="EN" onSelectMovie={onSelectMovie} onToggleWatchlist={() => {}} onToggleWatched={() => {}} {...props} />);

    expect(screen.getByAltText('Ice Age: The Great Egg-Scapade')).toHaveAttribute('src', '/ice-en.jpg');
    expect(screen.getByText('Animation')).toBeInTheDocument();
    expect(screen.queryByText(/Льодовиковий період/)).not.toBeInTheDocument();
    expect(screen.queryByText('Мультфільм')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Ice Age: The Great Egg-Scapade' }));
    expect(onSelectMovie).toHaveBeenCalledWith(iceAge);
  });

  it('shows the Ukrainian title and genre in Ukrainian', () => {
    render(<UserProfile user={user} language="UKR" initialTab="watchlist" watchlistMovies={[iceAge]} onSelectMovie={() => {}} onToggleWatchlist={() => {}} />);

    expect(screen.getByRole('button', { name: 'Льодовиковий період: Погоня за яйцями' })).toBeInTheDocument();
    expect(screen.getByText('Мультфільм')).toBeInTheDocument();
    expect(screen.getByAltText('Льодовиковий період: Погоня за яйцями')).toHaveAttribute('src', '/ice-uk.jpg');
  });
});
