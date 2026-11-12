import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import MovieDetails from './MovieDetails';

vi.mock('../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

const CONTENT_ID = '11111111-1111-4111-8111-111111111111';
// A card from the compact catalog list: no synopsis
const card = { id: 1, content_id: CONTENT_ID, title: 'Дюна', title_en: 'Dune', genre: 'Фантастика', year: 2024, rating: 8.5, description: null };

describe('MovieDetails synopsis from the full details', () => {
  beforeEach(() => vi.clearAllMocks());

  it('loads the synopsis of a title opened from the compact list', async () => {
    apiClient.get.mockImplementation(url => {
      if (url === `/movies/${CONTENT_ID}`) {
        return Promise.resolve({ data: { ...card, description: 'Пол Атрід об’єднується з фременами.' } });
      }
      return Promise.resolve({ data: { items: [] } });
    });

    render(<MovieDetails movie={card} user={null} isLoggedIn={false} openAuth={vi.fn()} onBack={vi.fn()} />);

    expect(screen.getByText('Завантаження опису…')).toBeInTheDocument();
    expect(await screen.findByText('Пол Атрід об’єднується з фременами.')).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith(`/movies/${CONTENT_ID}`);
  });

  it('says there is no synopsis when the details cannot be loaded', async () => {
    apiClient.get.mockImplementation(url =>
      url === `/movies/${CONTENT_ID}` ? Promise.reject(new Error('offline')) : Promise.resolve({ data: { items: [] } })
    );

    render(<MovieDetails movie={card} user={null} isLoggedIn={false} openAuth={vi.fn()} onBack={vi.fn()} />);

    expect(await screen.findByText('Опис цього фільму поки що відсутній.')).toBeInTheDocument();
  });

  it('shows the initial of the review author instead of an external avatar', async () => {
    apiClient.get.mockImplementation(url =>
      url.startsWith('/movies/')
        ? Promise.resolve({ data: card })
        : Promise.resolve({ data: { items: [{ review_id: 'r1', content_id: CONTENT_ID, user_id: 'u1', author_nickname: 'cinema_fan', rating: 9, review_text: 'Неймовірний візуальний шедевр!' }] } })
    );

    render(<MovieDetails movie={card} user={null} isLoggedIn={false} openAuth={vi.fn()} onBack={vi.fn()} />);

    expect(await screen.findByText('Неймовірний візуальний шедевр!')).toBeInTheDocument();
    expect(screen.getByText('C')).toBeInTheDocument();
    expect(document.querySelector('img[src*="picsum"]')).toBeNull();
  });
});
