import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import MovieExtras from './MovieExtras';

vi.mock('../api/client', () => ({ default: { get: vi.fn() } }));

const CONTENT_ID = '11111111-1111-4111-8111-111111111111';
const fellowship = { id: 2, content_id: '22222222-2222-4222-8222-222222222222', title: 'Хранителі персня', title_en: 'The Fellowship of the Ring', year: 2001, img: '/fotr.jpg' };
const king = { id: 3, content_id: '33333333-3333-4333-8333-333333333333', title: 'Повернення короля', title_en: 'The Return of the King', year: 2003, img: '/rotk.jpg' };

const movie = {
  id: 1,
  content_id: CONTENT_ID,
  title: 'Дві вежі',
  title_en: 'The Two Towers',
  trailer_uk: 'ukTrailer2',
  trailer_en: 'enNew00001',
  cast: [
    { name: 'Elijah Wood', character: 'Frodo', photo: null },
    { name: 'Ian McKellen', character: 'Gandalf', photo: 'https://image.tmdb.org/t/p/w185/ian.jpg' },
  ],
  crew: { directors: ['Peter Jackson'], writers: ['Fran Walsh', 'Philippa Boyens'], creators: [] },
  series: null,
};

const related = { collection: { id: 119, name: 'Володар перснів' }, collection_items: [fellowship, king], similar: [king] };

describe('MovieExtras: the page of a title from TMDB (US-013)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue({ data: related });
  });

  it('embeds the trailer in the interface language with the privacy-friendly YouTube player', async () => {
    // Trace: T-049
    const { rerender } = render(<MovieExtras movie={movie} isUkr />);

    expect(screen.getByTitle('Трейлер: Дві вежі')).toHaveAttribute('src', 'https://www.youtube-nocookie.com/embed/ukTrailer2');
    rerender(<MovieExtras movie={movie} isUkr={false} />);
    expect(screen.getByTitle('Trailer: The Two Towers')).toHaveAttribute('src', 'https://www.youtube-nocookie.com/embed/enNew00001');
    await screen.findByText(/All parts of the series/);
  });

  it('falls back to the trailer in the other language and hides the section without any', async () => {
    // Trace: T-049
    const { rerender } = render(<MovieExtras movie={{ ...movie, trailer_uk: null }} isUkr />);
    expect(screen.getByText('(англійською)')).toBeInTheDocument();
    expect(screen.getByTitle('Трейлер: Дві вежі')).toHaveAttribute('src', expect.stringContaining('enNew00001'));

    rerender(<MovieExtras movie={{ ...movie, trailer_uk: null, trailer_en: null }} isUkr />);
    expect(screen.queryByTitle(/Трейлер/)).not.toBeInTheDocument();
    await screen.findByText(/Усі частини серії/);
  });

  it('shows the crew and the cast with photos or initials', async () => {
    // Trace: T-049
    render(<MovieExtras movie={movie} isUkr />);

    const crew = screen.getByRole('region', { name: 'Знімальна група і актори' });
    expect(within(crew).getByText('Peter Jackson')).toBeInTheDocument();
    expect(within(crew).getByText('Fran Walsh, Philippa Boyens')).toBeInTheDocument();
    expect(within(crew).queryByText('Автори серіалу')).not.toBeInTheDocument();
    expect(within(crew).getByAltText('Ian McKellen')).toHaveAttribute('src', 'https://image.tmdb.org/t/p/w185/ian.jpg');
    expect(within(crew).getByText('Frodo')).toBeInTheDocument();
    expect(within(crew).getByText('E')).toBeInTheDocument();
    await screen.findByText(/Усі частини серії/);
  });

  it('shows the seasons, the status and the next episode of a series', async () => {
    // Trace: T-049
    apiClient.get.mockResolvedValue({ data: { collection: null, collection_items: [], similar: [] } });
    const series = {
      ...movie,
      trailer_uk: null,
      trailer_en: null,
      cast: [],
      crew: { directors: [], writers: [], creators: ['David Benioff'] },
      series: {
        status: 'Returning Series',
        number_of_seasons: 2,
        number_of_episodes: 18,
        next_episode: { air_date: '2026-12-01', season_number: 2, episode_number: 9, name: null },
        seasons: [
          { season_number: 1, name: 'Сезон 1', episode_count: 10, air_date: '2024-01-01', poster: '/s1.jpg' },
          { season_number: 2, name: null, episode_count: 8, air_date: '2026-10-01', poster: null },
        ],
      },
    };

    render(<MovieExtras movie={series} isUkr />);

    const seasons = screen.getByRole('region', { name: 'Сезони' });
    expect(within(seasons).getByText('Виходить')).toBeInTheDocument();
    expect(within(seasons).getByText('18')).toBeInTheDocument();
    expect(within(seasons).getByText(/01\.12\.2026 · S2E9/)).toBeInTheDocument();
    expect(within(seasons).getByText('Сезон 2')).toBeInTheDocument();
    expect(within(seasons).getByText('10 сер. · 2024')).toBeInTheDocument();
    expect(screen.getByText('David Benioff')).toBeInTheDocument();
  });

  it('lists the other parts of the film series and similar titles, and opens them', async () => {
    // Trace: T-049
    const onSelectMovie = vi.fn();
    render(<MovieExtras movie={movie} isUkr onSelectMovie={onSelectMovie} />);

    const parts = await screen.findByRole('region', { name: 'Усі частини серії' });
    expect(within(parts).getByText(/Володар перснів/, { selector: 'h3' })).toBeInTheDocument();
    expect(within(parts).getAllByRole('button').map(button => button.textContent)).toEqual(['Хранителі персня2001', 'Повернення короля2003']);
    expect(apiClient.get).toHaveBeenCalledWith(`/movies/${CONTENT_ID}/related`);

    await userEvent.click(within(screen.getByRole('region', { name: 'Схожі' })).getByRole('button', { name: /Повернення короля/ }));
    expect(onSelectMovie).toHaveBeenCalledWith(king);
  });

  it('shows nothing extra for a title without TMDB details', async () => {
    // Trace: T-049
    apiClient.get.mockRejectedValue(new Error('offline'));
    const { container } = render(<MovieExtras movie={{ id: 5, content_id: 'local-5', title: 'Фільм' }} isUkr />);

    expect(container).toBeEmptyDOMElement();
    expect(apiClient.get).not.toHaveBeenCalled();
  });
});
