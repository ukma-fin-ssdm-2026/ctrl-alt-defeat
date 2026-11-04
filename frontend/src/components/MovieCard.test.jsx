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