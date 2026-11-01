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
        params: { sort_by: 'release_date', order: 'desc' },
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
        params: { genre: 'Драма', sort_by: 'rating', order: 'desc' },
      })
    );
    expect(screen.queryByText('New SciFi')).not.toBeInTheDocument();
    expect(renderedTitles()).toEqual(['Old Drama', 'New Drama']);
  });
});
