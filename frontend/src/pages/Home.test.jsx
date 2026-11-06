import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import Home from './Home';

vi.mock('../api/client', () => ({
  default: { get: vi.fn() },
}));

const catalog = [
  { id: 1, title: 'Old Drama', genre: 'Драма', category: 'Movie', rating: 9.3, year: 1994, runtime: 142 },
  { id: 2, title: 'New SciFi', genre: 'Фантастика', category: 'Movie', rating: 8.8, year: 2024, runtime: 166 },
  { id: 3, title: 'New Drama', genre: 'Драма', category: 'Movie', rating: 8.5, year: 2019, runtime: 132 },
];

const renderedTitles = () =>
  catalog
    .map(movie => movie.title)
    .filter(title => screen.queryByText(title))
    .sort((a, b) => {
      const position = title => {
        const node = screen.getByText(title);
        return Array.from(document.body.querySelectorAll('*')).indexOf(node);
      };
      return position(a) - position(b);
    });

describe('Home catalog sorting (FR-010)', () => {
  beforeEach(() => {
    apiClient.get.mockReset();
    apiClient.get.mockResolvedValue({ data: { items: catalog } });
  });

  it('renders a sort select with the default option', async () => {
    render(<Home onSelectMovie={() => {}} />);
    const select = await screen.findByRole('combobox', { name: 'Сортування' });
    expect(select).toHaveValue('');
    expect(within(select).getByRole('option', { name: 'За рейтингом (спершу найвищий)' })).toBeInTheDocument();
  });

  it('requests sorted data from the API when a criterion is chosen', async () => {
    render(<Home onSelectMovie={() => {}} />);
    await screen.findByText('Old Drama');

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Сортування' }), 'release_date_desc');

    await waitFor(() =>
      expect(apiClient.get).toHaveBeenLastCalledWith('/movies', {
        params: { sort_by: 'release_date', order: 'desc', skip: 0, limit: 100 },
      })
    );
  });

  it('reorders the list instantly, newest release first', async () => {
    render(<Home onSelectMovie={() => {}} />);
    await screen.findByText('Old Drama');

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Сортування' }), 'release_date_desc');

    expect(renderedTitles()).toEqual(['New SciFi', 'New Drama', 'Old Drama']);
  });

  it('sends filters together with sorting so only the filtered selection is sorted', async () => {
    render(<Home selectedGenre="Драма" onSelectMovie={() => {}} />);
    await screen.findByText('Old Drama');

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Сортування' }), 'rating_desc');

    await waitFor(() =>
      expect(apiClient.get).toHaveBeenLastCalledWith('/movies', {
        params: { genre: 'Драма', sort_by: 'rating', order: 'desc', skip: 0, limit: 100 },
      })
    );
    expect(screen.queryByText('New SciFi')).not.toBeInTheDocument();
    expect(renderedTitles()).toEqual(['Old Drama', 'New Drama']);
  });
});

describe('Home cartoons category', () => {
  beforeEach(() => apiClient.get.mockReset());

  it('asks the API for cartoons and shows them', async () => {
    const cartoon = { id: 9, title: 'Шрек', genre: 'Мультфільм', category: 'Cartoons', rating: 7.9, year: 2001 };
    apiClient.get.mockResolvedValue({ data: { items: [cartoon] } });
    render(<Home selectedCategory="Мультфільми" onSelectMovie={() => {}} />);

    expect(await screen.findByText('Шрек')).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith('/movies', expect.objectContaining({ params: expect.objectContaining({ category: 'Cartoons' }) }));
  });
});

describe('Home shows the whole catalog', () => {
  beforeEach(() => apiClient.get.mockReset());

  const page = (from, count, total) => ({
    data: {
      items: Array.from({ length: count }, (_, i) => ({ id: from + i, title: `Фільм ${from + i}`, genre: 'Драма', category: 'Movie', year: 2020 })),
      total,
      has_more: from - 1 + count < total,
    },
  });

  it('loads every page at once, without a "Show more" button', async () => {
    apiClient.get.mockResolvedValueOnce(page(1, 100, 130)).mockResolvedValueOnce(page(101, 30, 130));
    render(<Home selectedCategory="Фільми" onSelectMovie={() => {}} />);

    expect(await screen.findByText('Фільм 130')).toBeInTheDocument();
    expect(screen.getByText('Усього: 130')).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenLastCalledWith('/movies', { params: { category: 'Movie', skip: 100, limit: 100 } });
    expect(screen.queryByRole('button', { name: 'Показати ще' })).not.toBeInTheDocument();
  });

  it('never shows placeholder titles: an empty result and an unavailable server say so', async () => {
    apiClient.get.mockResolvedValueOnce({ data: { items: [], total: 0, has_more: false } });
    const { unmount } = render(<Home selectedGenre="Вестерн" onSelectMovie={() => {}} />);
    expect(await screen.findByText('Не знайдено жодного фільму за такими критеріями.')).toBeInTheDocument();
    unmount();

    apiClient.get.mockRejectedValueOnce(new Error('offline'));
    render(<Home onSelectMovie={() => {}} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Каталог тимчасово недоступний');
  });
});
