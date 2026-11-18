import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import MovieCard from './MovieCard';

const movie = {
  id: 1,
  title: 'Тестовий фільм',
  title_en: 'Test Movie',
  img: '/test.jpg',
  category: 'Фільми',
  rating: 8.5,
  year: 2024,
  genre: 'Драма',
};

describe('MovieCard accessibility (S6848)', () => {
  it('opens movie details when the card button is clicked', () => {
    const onSelect = vi.fn();

    render(<MovieCard movie={movie} onSelect={onSelect} />);

    fireEvent.click(screen.getByRole('button', { name: /Тестовий фільм/ }));

    expect(onSelect).toHaveBeenCalledWith(movie);
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it('toggles watchlist without opening movie details', () => {
    const onSelect = vi.fn();
    const onToggleWatchlist = vi.fn();

    render(
      <MovieCard
        movie={movie}
        onSelect={onSelect}
        onToggleWatchlist={onToggleWatchlist}
        isWatchlisted={false}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Додати до списку' }));

    expect(onToggleWatchlist).toHaveBeenCalledWith(movie.id);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('uses native buttons for both interactive actions', () => {
    render(
      <MovieCard
        movie={movie}
        onSelect={vi.fn()}
        onToggleWatchlist={vi.fn()}
        isWatchlisted={false}
      />
    );

    const buttons = screen.getAllByRole('button');

    expect(buttons).toHaveLength(2);
    buttons.forEach((button) => {
      expect(button).toHaveAttribute('type', 'button');
    });
  });
});
describe('MovieCard poster in the interface language (T-050)', () => {
  const localized = { ...movie, img: '/uk-poster.jpg', img_en: '/en-poster.jpg' };

  it('shows the Ukrainian poster in Ukrainian and the English one in English', () => {
    const { rerender } = render(<MovieCard movie={localized} onSelect={vi.fn()} />);
    expect(screen.getByAltText('Тестовий фільм')).toHaveAttribute('src', '/uk-poster.jpg');

    rerender(<MovieCard movie={localized} onSelect={vi.fn()} language="EN" />);
    expect(screen.getByAltText('Test Movie')).toHaveAttribute('src', '/en-poster.jpg');
  });

  it('keeps the main poster in English when there is no English one', () => {
    render(<MovieCard movie={{ ...localized, img_en: null }} onSelect={vi.fn()} language="EN" />);
    expect(screen.getByAltText('Test Movie')).toHaveAttribute('src', '/uk-poster.jpg');
  });
});
