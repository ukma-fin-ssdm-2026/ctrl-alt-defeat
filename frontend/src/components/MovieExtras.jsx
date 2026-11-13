import { useEffect, useState } from 'react';
import apiClient from '../api/client';

// Details of the page of a title from TMDB (US-013): trailer, crew and cast, seasons of a series,
// other parts of the film series and similar titles.

const SERIES_STATUS = {
  'Returning Series': ['Виходить', 'Returning'],
  Ended: ['Завершено', 'Ended'],
  Canceled: ['Скасовано', 'Canceled'],
  'In Production': ['У виробництві', 'In production'],
  Planned: ['Заплановано', 'Planned'],
  Pilot: ['Пілот', 'Pilot'],
};

const isUuid = value => typeof value === 'string' && /^[0-9a-f-]{36}$/i.test(value);

const formatDate = (value, isUkr) => {
  if (!value) return '';
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(isUkr ? 'uk-UA' : 'en-GB');
};

// Trailer in the interface language, otherwise in the other one
function chooseTrailer(movie, isUkr) {
  const own = isUkr ? movie.trailer_uk : movie.trailer_en;
  const other = isUkr ? movie.trailer_en : movie.trailer_uk;
  if (own) return { key: own, otherLanguage: false };
  if (other) return { key: other, otherLanguage: true };
  return null;
}

const sectionClass = 'mb-12 bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700';
const headingClass = 'text-lg font-bold mb-4 text-gray-900 dark:text-white border-l-4 border-yellow-500 pl-3';

function TitleRow({ titles, isUkr, onSelectMovie }) {
  return (
    <ul className="flex gap-4 overflow-x-auto pb-2">
      {titles.map(title => {
        const name = isUkr ? title.title : (title.title_en || title.title);
        return (
          <li key={title.content_id || title.id} className="w-28 shrink-0">
            <button type="button" onClick={() => onSelectMovie?.(title)} className="text-left w-full group">
              <img src={title.img} alt={name} loading="lazy" className="w-28 aspect-[2/3] object-cover rounded-lg shadow-sm group-hover:ring-2 group-hover:ring-yellow-500" />
              <span className="block mt-1 text-xs font-semibold text-gray-900 dark:text-gray-100 line-clamp-2">{name}</span>
              <span className="block text-[11px] text-gray-500 dark:text-gray-400">{title.year}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export default function MovieExtras({ movie, isUkr, onSelectMovie }) {
  const contentId = movie.content_id;
  const [related, setRelated] = useState({ key: null, data: null });

  useEffect(() => {
    if (!isUuid(contentId)) return undefined;
    let ignore = false;
    Promise.resolve(apiClient.get(`/movies/${contentId}/related`))
      .then(response => { if (!ignore) setRelated({ key: contentId, data: response?.data || null }); })
      .catch(() => { if (!ignore) setRelated({ key: contentId, data: null }); });
    return () => { ignore = true; };
  }, [contentId]);

  const relatedData = related.key === contentId ? related.data : null;
  const parts = relatedData?.collection_items || [];
  const similar = relatedData?.similar || [];
  const trailer = chooseTrailer(movie, isUkr);
  const cast = movie.cast || [];
  const crew = movie.crew || {};
  const series = movie.series;
  const title = isUkr ? movie.title : (movie.title_en || movie.title);

  // A related title opens at the top of its page
  const openTitle = item => {
    onSelectMovie?.(item);
    if (typeof window.scrollTo === 'function') {
      try { window.scrollTo({ top: 0 }); } catch { /* not available in tests */ }
    }
  };

  const crewLines = [
    [isUkr ? 'Режисер' : 'Director', crew.directors],
    [isUkr ? 'Сценарій' : 'Writers', crew.writers],
    [isUkr ? 'Автори серіалу' : 'Created by', crew.creators],
  ].filter(([, names]) => names && names.length > 0);

  const status = series?.status ? (SERIES_STATUS[series.status] || [series.status, series.status])[isUkr ? 0 : 1] : null;
  const next = series?.next_episode;

  return (
    <>
      {trailer && (
        <section className={sectionClass} aria-label={isUkr ? 'Трейлер' : 'Trailer'}>
          <h3 className={headingClass}>
            {isUkr ? 'Трейлер' : 'Trailer'}
            {trailer.otherLanguage && (
              <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">
                {isUkr ? '(англійською)' : '(in Ukrainian)'}
              </span>
            )}
          </h3>
          <div className="aspect-video w-full overflow-hidden rounded-xl bg-black">
            <iframe
              className="w-full h-full"
              src={`https://www.youtube-nocookie.com/embed/${trailer.key}`}
              title={`${isUkr ? 'Трейлер' : 'Trailer'}: ${title}`}
              loading="lazy"
              allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen"
              referrerPolicy="strict-origin-when-cross-origin"
              allowFullScreen
            />
          </div>
        </section>
      )}

      {(crewLines.length > 0 || cast.length > 0) && (
        <section className={sectionClass} aria-label={isUkr ? 'Знімальна група і актори' : 'Crew and cast'}>
          <h3 className={headingClass}>{isUkr ? 'У ролях' : 'Cast'}</h3>
          {crewLines.length > 0 && (
            <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm mb-5">
              {crewLines.map(([label, names]) => (
                <div key={label}>
                  <dt className="text-gray-500 dark:text-gray-400 font-semibold">{label}</dt>
                  <dd className="text-gray-900 dark:text-gray-200 font-medium">{names.join(', ')}</dd>
                </div>
              ))}
            </dl>
          )}
          {cast.length > 0 && (
            <ul className="flex gap-4 overflow-x-auto pb-2">
              {cast.map(person => (
                <li key={`${person.name}|${person.character}`} className="w-24 shrink-0 text-center">
                  {person.photo ? (
                    <img src={person.photo} alt={person.name} loading="lazy" className="w-20 h-20 mx-auto rounded-full object-cover shadow-sm" />
                  ) : (
                    <span aria-hidden="true" className="w-20 h-20 mx-auto rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-2xl font-black flex items-center justify-center">
                      {person.name[0]}
                    </span>
                  )}
                  <span className="block mt-2 text-xs font-semibold text-gray-900 dark:text-gray-100">{person.name}</span>
                  {person.character && <span className="block text-[11px] text-gray-500 dark:text-gray-400">{person.character}</span>}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {series && (
        <section className={sectionClass} aria-label={isUkr ? 'Сезони' : 'Seasons'}>
          <h3 className={headingClass}>{isUkr ? 'Сезони і серії' : 'Seasons and episodes'}</h3>
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm mb-5">
            {status && (
              <div>
                <dt className="text-gray-500 dark:text-gray-400 font-semibold">{isUkr ? 'Статус' : 'Status'}</dt>
                <dd className="text-gray-900 dark:text-gray-200 font-medium">{status}</dd>
              </div>
            )}
            {series.number_of_seasons != null && (
              <div>
                <dt className="text-gray-500 dark:text-gray-400 font-semibold">{isUkr ? 'Сезонів' : 'Seasons'}</dt>
                <dd className="text-gray-900 dark:text-gray-200 font-medium">{series.number_of_seasons}</dd>
              </div>
            )}
            {series.number_of_episodes != null && (
              <div>
                <dt className="text-gray-500 dark:text-gray-400 font-semibold">{isUkr ? 'Серій' : 'Episodes'}</dt>
                <dd className="text-gray-900 dark:text-gray-200 font-medium">{series.number_of_episodes}</dd>
              </div>
            )}
            {next?.air_date && (
              <div>
                <dt className="text-gray-500 dark:text-gray-400 font-semibold">{isUkr ? 'Наступна серія' : 'Next episode'}</dt>
                <dd className="text-gray-900 dark:text-gray-200 font-medium">
                  {formatDate(next.air_date, isUkr)}
                  {next.season_number != null && next.episode_number != null && ` · S${next.season_number}E${next.episode_number}`}
                </dd>
              </div>
            )}
          </dl>
          {series.seasons?.length > 0 && (
            <ul className="flex gap-4 overflow-x-auto pb-2">
              {series.seasons.map(season => (
                <li key={season.season_number} className="w-28 shrink-0">
                  {season.poster ? (
                    <img src={season.poster} alt={season.name || ''} loading="lazy" className="w-28 aspect-[2/3] object-cover rounded-lg shadow-sm" />
                  ) : (
                    <span aria-hidden="true" className="w-28 aspect-[2/3] rounded-lg bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-gray-500 text-xl font-black">
                      {season.season_number}
                    </span>
                  )}
                  <span className="block mt-1 text-xs font-semibold text-gray-900 dark:text-gray-100">
                    {season.name || `${isUkr ? 'Сезон' : 'Season'} ${season.season_number}`}
                  </span>
                  <span className="block text-[11px] text-gray-500 dark:text-gray-400">
                    {season.episode_count != null && `${season.episode_count} ${isUkr ? 'сер.' : 'ep.'}`}
                    {season.air_date && ` · ${season.air_date.slice(0, 4)}`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {relatedData?.collection && parts.length > 0 && (
        <section className={sectionClass} aria-label={isUkr ? 'Усі частини серії' : 'All parts of the series'}>
          <h3 className={headingClass}>
            {isUkr ? 'Усі частини серії' : 'All parts of the series'}: {relatedData.collection.name}
          </h3>
          <TitleRow titles={parts} isUkr={isUkr} onSelectMovie={openTitle} />
        </section>
      )}

      {similar.length > 0 && (
        <section className={sectionClass} aria-label={isUkr ? 'Схожі' : 'Similar'}>
          <h3 className={headingClass}>{isUkr ? 'Схожі' : 'Similar titles'}</h3>
          <TitleRow titles={similar} isUkr={isUkr} onSelectMovie={openTitle} />
        </section>
      )}
    </>
  );
}
