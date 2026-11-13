import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import Header from './Header';

// The genre menu asks the server for genres; offline the built-in list is used
vi.mock('../api/client', () => ({ default: { get: vi.fn(() => Promise.reject(new Error('offline'))) } }));

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

const dune = { id: 7, title: 'Дюна', titleEn: 'Dune', year: 2021, genre: 'Фантастика', img: '/dune.jpg' };

describe('Header behaviour kept by the Lab 8 refactoring (S6848)', () => {
  it('goes to the home page from the logo', async () => {
    const onGoHome = vi.fn();
    render(<Header {...baseProps} user={null} onGoHome={onGoHome} />);

    await userEvent.click(screen.getByAltText('Після титрів'));
    expect(onGoHome).toHaveBeenCalledTimes(1);
  });

  it('opens a movie from the search suggestions and clears the search', async () => {
    const onSelectMovie = vi.fn();
    render(<Header {...baseProps} user={null} movies={[dune]} onSelectMovie={onSelectMovie} />);
    const search = screen.getByPlaceholderText('Пошук ...');

    await userEvent.type(search, 'дю');
    await userEvent.click(screen.getByText('Дюна'));

    expect(onSelectMovie).toHaveBeenCalledWith(dune);
    expect(search).toHaveValue('');
    expect(screen.queryByText('Дюна')).not.toBeInTheDocument();
  });
});

describe('Header interactive elements are native buttons (SonarQube S6848)', () => {
  it('the logo is a button reachable with the keyboard', async () => {
    const onGoHome = vi.fn();
    render(<Header {...baseProps} user={null} onGoHome={onGoHome} />);

    const logo = screen.getByRole('button', { name: /Після титрів/ });
    logo.focus();
    await userEvent.keyboard('{Enter}');
    expect(onGoHome).toHaveBeenCalledTimes(1);
  });

  it('each search suggestion is a button reachable with the keyboard', async () => {
    const onSelectMovie = vi.fn();
    render(<Header {...baseProps} user={null} movies={[dune]} onSelectMovie={onSelectMovie} />);

    await userEvent.type(screen.getByPlaceholderText('Пошук ...'), 'dune');
    const suggestion = screen.getByRole('button', { name: /Дюна/ });
    suggestion.focus();
    await userEvent.keyboard('{Enter}');
    expect(onSelectMovie).toHaveBeenCalledWith(dune);
  });
});

describe('Header admin entry (FR-009)', () => {
  it('shows the Users page button only to administrators', async () => {
    const onGoAdmin = vi.fn();
    const { rerender } = render(<Header {...baseProps} user={{ user_id: 'u1', nickname: 'viewer', role: 'user' }} onGoProfile={vi.fn()} onGoAdmin={onGoAdmin} />);
    expect(screen.queryByRole('button', { name: 'Користувачі' })).not.toBeInTheDocument();

    rerender(<Header {...baseProps} user={{ user_id: 'u2', nickname: 'admin', role: 'admin' }} onGoProfile={vi.fn()} onGoAdmin={onGoAdmin} />);
    await userEvent.click(screen.getByRole('button', { name: 'Користувачі' }));
    expect(onGoAdmin).toHaveBeenCalledTimes(1);
  });
});

describe('Header search suggestions follow the interface language', () => {
  // As the API sends it: `title_en`, not `titleEn`
  const rings = { id: 9, title: 'Володар перснів: Дві вежі', title_en: 'The Lord of the Rings: The Two Towers', year: 2002, genre: 'Пригоди', img: '/ttt.jpg' };
  const noEnglish = { id: 10, title: 'Захар Беркут', title_en: null, year: 2019, genre: 'Драма', img: '/zb.jpg' };

  it('shows the English title first when the interface is in English', async () => {
    render(<Header {...baseProps} language="EN" user={null} movies={[rings]} />);

    await userEvent.type(screen.getByPlaceholderText('Search ...'), 'lord of the');

    const suggestion = screen.getByRole('button', { name: /The Lord of the Rings: The Two Towers/ });
    // The Ukrainian title is the second line
    expect(suggestion).toHaveTextContent('Володар перснів: Дві вежі • 2002');
    expect(screen.getByAltText('The Lord of the Rings: The Two Towers')).toBeInTheDocument();
  });

  it('shows the Ukrainian title first in Ukrainian, with the English one below', async () => {
    render(<Header {...baseProps} user={null} movies={[rings]} />);

    await userEvent.type(screen.getByPlaceholderText('Пошук ...'), 'lord');

    expect(screen.getByAltText('Володар перснів: Дві вежі')).toBeInTheDocument();
    expect(screen.getByText(/The Lord of the Rings: The Two Towers • 2002/)).toBeInTheDocument();
  });

  it('falls back to the Ukrainian title without repeating it when there is no English one', async () => {
    render(<Header {...baseProps} language="EN" user={null} movies={[noEnglish]} />);

    await userEvent.type(screen.getByPlaceholderText('Search ...'), 'захар');

    expect(screen.getByAltText('Захар Беркут')).toBeInTheDocument();
    expect(screen.queryByText(/Захар Беркут •/)).not.toBeInTheDocument();
  });
});
