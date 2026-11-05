import { useEffect, useState } from 'react';
import apiClient from '../api/client';

// Shown until the server answers, and if it is unavailable
export const FALLBACK_GENRES = [
  'Бойовик', 'Комедія', 'Драма', 'Фантастика', 'Жахи',
  'Трилер', 'Детектив', 'Документальний', 'Біографія',
  'Історія', 'Мелодрама', 'Кримінал', 'Музика', 'Пригоди',
];

// Genres of the catalog that have at least one title (GET /genres, FR-012, US-012)
export default function useCatalogGenres() {
  const [genres, setGenres] = useState(FALLBACK_GENRES);

  useEffect(() => {
    let ignore = false;
    apiClient.get('/genres')
      .then(response => {
        const names = (Array.isArray(response.data) ? response.data : []).map(genre => genre.name).filter(Boolean);
        if (!ignore && names.length > 0) setGenres(names);
      })
      .catch(() => {
        // Keep the built-in list
      });
    return () => { ignore = true; };
  }, []);

  return genres;
}
