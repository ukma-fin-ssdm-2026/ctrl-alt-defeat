import { render, screen } from '@testing-library/react';
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

    expect(await screen.findByText('Нагороди та досягнення 🏆')).toBeInTheDocument();
    expect(screen.getByTestId('badge-planner')).toHaveClass('achievement-highlight');
    expect(screen.getByTestId('badge-reviewer')).not.toHaveClass('achievement-highlight');
  });
});
