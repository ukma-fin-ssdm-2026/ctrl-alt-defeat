import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import Header from './Header';

const baseProps = {
  toggleTheme: () => {},
  isDarkMode: false,
  openAuth: vi.fn(),
  onLogout: vi.fn(),
  onGoHome: () => {},
  onToggleLanguage: () => {},
  movies: [],
  onSelectMovie: () => {},
  onSelectCategory: () => {},
  onSelectGenre: () => {},
  onApplyFilter: () => {},
  language: 'UKR',
};

describe('Header profile button (FR-001)', () => {
  it('shows the nickname of the logged-in user and opens the profile', async () => {
    // Trace: T-037
    const onGoProfile = vi.fn();
    render(<Header {...baseProps} user={{ user_id: 'u1', nickname: 'admin', email: 'admin@gmail.com' }} onGoProfile={onGoProfile} />);

    const profileButton = screen.getByRole('button', { name: 'Мій профіль' });
    expect(profileButton).toHaveTextContent('admin');
    expect(profileButton).toHaveTextContent('A');

    await userEvent.click(profileButton);
    expect(onGoProfile).toHaveBeenCalledTimes(1);
  });

  it('shows the login button for a guest', () => {
    // Trace: T-037
    render(<Header {...baseProps} user={null} onGoProfile={vi.fn()} />);

    expect(screen.queryByRole('button', { name: 'Мій профіль' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Увійти' })).toBeInTheDocument();
  });
});
