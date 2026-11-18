import { describe, expect, it } from 'vitest';
import { posterFor } from './poster';

describe('poster in the interface language', () => {
  const movie = { img: '/uk.jpg', img_en: '/en.jpg' };

  it('shows the Ukrainian poster in Ukrainian and the English one in English', () => {
    expect(posterFor(movie, 'UKR')).toBe('/uk.jpg');
    expect(posterFor(movie, 'EN')).toBe('/en.jpg');
  });

  it('falls back to the main poster without an English one', () => {
    expect(posterFor({ img: '/uk.jpg', img_en: null }, 'EN')).toBe('/uk.jpg');
    expect(posterFor({ img: '/only.jpg' }, 'EN')).toBe('/only.jpg');
    expect(posterFor(null, 'EN')).toBeUndefined();
  });
});
