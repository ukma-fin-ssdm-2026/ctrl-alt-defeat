import { useEffect, useState } from 'react';
import apiClient from '../api/client';
import { CURRENT_USER_ID } from '../auth/currentUser';
import { isUuid } from '../utils/uuid';

// Must match MAX_COMMENT_DEPTH on the backend (0 = top-level comment)
export const MAX_COMMENT_DEPTH = 4;

const texts = {
  UKR: {
    show: 'Коментарі',
    hide: 'Сховати коментарі',
    loading: 'Завантаження коментарів...',
    empty: 'Коментарів ще немає. Почніть обговорення!',
    loadError: 'Не вдалося завантажити коментарі.',
    placeholder: 'Напишіть коментар...',
    replyPlaceholder: 'Ваша відповідь...',
    send: 'Відправити',
    sending: 'Відправка...',
    reply: 'Відповісти',
    cancel: 'Скасувати',
    emptyText: 'Текст коментаря не може бути порожнім',
    authRequired: 'Будь ласка, авторизуйтесь, щоб залишити коментар',
    policy: 'Коментар містить заборонений вміст (HTML, посилання або образи).',
    failed: 'Не вдалося надіслати коментар.',
    commentLabel: 'Коментар',
  },
  EN: {
    show: 'Comments',
    hide: 'Hide comments',
    loading: 'Loading comments...',
    empty: 'No comments yet. Start the discussion!',
    loadError: 'Failed to load comments.',
    placeholder: 'Write a comment...',
    replyPlaceholder: 'Your reply...',
    send: 'Send',
    sending: 'Sending...',
    reply: 'Reply',
    cancel: 'Cancel',
    emptyText: 'Comment text cannot be empty',
    authRequired: 'Please log in to leave a comment',
    policy: 'The comment contains forbidden content (HTML, links or insults).',
    failed: 'Failed to send the comment.',
    commentLabel: 'Comment',
  },
};

function CommentForm({ reviewId, parentId, isLoggedIn, openAuth, user, t, placeholder, onPosted, onCancel }) {
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  const requireAuth = () => {
    if (isLoggedIn) return false;
    setError(t.authRequired);
    openAuth?.();
    return true;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (requireAuth()) return;
    if (!text.trim()) {
      setError(t.emptyText);
      return;
    }

    if (!isUuid(reviewId)) {
      setError(t.failed);
      return;
    }

    setError('');
    setSending(true);
    // Constant URL: the review id travels in the request body
    apiClient.post('/comments', {
      review_id: reviewId,
      user_id: (user && (user.user_id || user.id)) || CURRENT_USER_ID,
      author_name: user?.nickname || user?.username || user?.email || 'Viewer',
      text: text.trim(),
      ...(parentId ? { parent_id: parentId } : {}),
    })
      .then(() => {
        setText('');
        setSending(false);
        onPosted();
      })
      .catch(err => {
        const status = err.response?.status;
        if (status === 401) setError(t.authRequired);
        else if (status === 422) setError(t.emptyText);
        else if (status === 400) setError(t.policy);
        else setError(err.response?.data?.error?.message || t.failed);
        setSending(false);
      });
  };

  return (
    <form onSubmit={handleSubmit} className="mt-2 flex flex-col gap-2">
      <textarea
        rows="2"
        value={text}
        aria-label={t.commentLabel}
        onFocus={requireAuth}
        onChange={(e) => { setText(e.target.value); if (error) setError(''); }}
        placeholder={placeholder}
        maxLength={2000}
        className="w-full p-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:outline-none focus:ring-2 focus:ring-yellow-500 text-sm"
      />
      {error && <p role="alert" className="text-xs text-red-600 dark:text-red-400">{error}</p>}
      <div className="flex gap-2 justify-end">
        {onCancel && (
          <button type="button" onClick={onCancel} className="px-3 py-1 text-xs text-gray-500 hover:underline">
            {t.cancel}
          </button>
        )}
        <button
          type="submit"
          disabled={sending}
          className="px-4 py-1.5 bg-yellow-500 hover:bg-yellow-600 disabled:opacity-50 text-gray-900 font-bold rounded-lg text-xs transition-colors"
        >
          {sending ? t.sending : t.send}
        </button>
      </div>
    </form>
  );
}

function CommentItem({ comment, reviewId, isLoggedIn, openAuth, user, t, language, onPosted }) {
  const [replying, setReplying] = useState(false);
  const time = new Date(comment.created_at).toLocaleString(language === 'UKR' ? 'uk-UA' : 'en-US');

  return (
    <li className="mt-3">
      <div className="bg-gray-50 dark:bg-gray-900/40 rounded-lg p-3">
        <div className="flex items-center gap-2 text-xs">
          <span className="font-bold text-gray-900 dark:text-white">{comment.author_name}</span>
          <time dateTime={comment.created_at} className="text-gray-400">{time}</time>
        </div>
        {/* Rendered as plain text: React escapes it, so markup is never executed */}
        <p className="text-sm text-gray-700 dark:text-gray-300 mt-1 whitespace-pre-line break-words">{comment.text}</p>
        {comment.depth < MAX_COMMENT_DEPTH && !replying && (
          <button
            onClick={() => setReplying(true)}
            className="mt-1 text-xs font-semibold text-yellow-600 dark:text-yellow-400 hover:underline"
          >
            {t.reply}
          </button>
        )}
        {replying && (
          <CommentForm
            reviewId={reviewId}
            parentId={comment.comment_id}
            isLoggedIn={isLoggedIn}
            openAuth={openAuth}
            user={user}
            t={t}
            placeholder={t.replyPlaceholder}
            onPosted={() => { setReplying(false); onPosted(); }}
            onCancel={() => setReplying(false)}
          />
        )}
      </div>
      {comment.replies?.length > 0 && (
        <ul className="pl-4 border-l-2 border-gray-100 dark:border-gray-700 ml-2">
          {comment.replies.map(reply => (
            <CommentItem
              key={reply.comment_id}
              comment={reply}
              reviewId={reviewId}
              isLoggedIn={isLoggedIn}
              openAuth={openAuth}
              user={user}
              t={t}
              language={language}
              onPosted={onPosted}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

// Threaded comments under a review (FR-011)
export default function ReviewComments({ reviewId, isLoggedIn, openAuth, user, language = 'UKR' }) {
  const t = texts[language] || texts.UKR;
  const [open, setOpen] = useState(false);
  const [version, setVersion] = useState(0); // bump to reload the thread
  const [thread, setThread] = useState(null); // { version, data } or { version, error }

  useEffect(() => {
    if (!open || !isUuid(reviewId)) return undefined;
    let ignore = false;
    apiClient.get('/comments', { params: { review_id: reviewId } })
      .then(response => { if (!ignore) setThread({ version, data: response.data }); })
      .catch(() => { if (!ignore) setThread({ version, error: true }); });
    return () => { ignore = true; };
  }, [open, reviewId, version]);

  const reload = () => setVersion(v => v + 1);
  // Only reviews stored on the backend (UUID ids) can have comments
  if (!isUuid(reviewId)) return null;

  // Keep showing the previous thread while a reload is in flight
  const data = thread?.data;
  const loading = !thread || (thread.version !== version && !data);

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="text-xs font-semibold text-gray-500 hover:text-yellow-600 dark:hover:text-yellow-400"
      >
        💬 {open ? t.hide : `${t.show}${data ? ` (${data.total})` : ''}`}
      </button>

      {open && (
        <div className="mt-2">
          {loading ? (
            <p className="text-xs text-gray-500">{t.loading}</p>
          ) : thread.error && !data ? (
            <p className="text-xs text-red-500">{t.loadError}</p>
          ) : data.items.length === 0 ? (
            <p className="text-xs text-gray-500">{t.empty}</p>
          ) : (
            <ul>
              {data.items.map(comment => (
                <CommentItem
                  key={comment.comment_id}
                  comment={comment}
                  reviewId={reviewId}
                  isLoggedIn={isLoggedIn}
                  openAuth={openAuth}
                  user={user}
                  t={t}
                  language={language}
                  onPosted={reload}
                />
              ))}
            </ul>
          )}
          <CommentForm
            reviewId={reviewId}
            isLoggedIn={isLoggedIn}
            openAuth={openAuth}
            user={user}
            t={t}
            placeholder={t.placeholder}
            onPosted={reload}
          />
        </div>
      )}
    </div>
  );
}
