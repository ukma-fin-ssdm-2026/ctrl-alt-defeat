// Poster in the interface language: the English interface shows the English poster (or one without text)
// when TMDB has it, otherwise the main poster, which is Ukrainian when TMDB has a Ukrainian one.
export function posterFor(movie, language) {
  if (!movie) return undefined;
  return language === 'UKR' ? movie.img : (movie.img_en || movie.img);
}
