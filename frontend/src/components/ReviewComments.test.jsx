import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import { CURRENT_USER_ID } from '../auth/currentUser';
import ReviewComments, { MAX_COMMENT_DEPTH } from './ReviewComments';

vi.mock('../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

const REVIEW_ID = '11111111-1111-4111-8111-111111111111';
const user = { username: 'admin', email: 'admin@gmail.com' };

const comment = (id, text, depth = 0, replies = [], author = 'olena') => ({
  comment_id: id,
  review_id: REVIEW_ID,
  parent_id: null,
  user_id: 'u1',
  author_name: author,
  text,
  depth,
  created_at: '2026-11-01T15:30:00Z',
  replies,
});

const thread = (items, total) => ({ data: { items, total: total ?? items.length } });

const openThread = async () => {
  await userEvent.click(screen.getByRole('button', { name: /Коментарі/ }));
};

const renderComments = (props = {}) =>
  render(<ReviewComments reviewId={REVIEW_ID} isLoggedIn user={user} openAuth={vi.fn()} {...props} />);

describe('ReviewComments (FR-011)', () => {
  beforeEach(() => {
    apiClient.get.mockReset();
    apiClient.post.mockReset();
  });

  it('loads the thread only when opened and shows nested replies with author and time', async () => {
    // Trace: T-029
    apiClient.get.mockResolvedValue(
      thread([comment('c1', 'Great review!', 0, [comment('c2', 'Agreed', 1, [], 'taras')])], 2)
    );
    renderComments();
    expect(apiClient.get).not.toHaveBeenCalled();

    await openThread();

    expect(await screen.findByText('Great review!')).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith('/comments', { params: { review_id: REVIEW_ID } });
    const reply = screen.getByText('Agreed').closest('li');
    expect(within(reply).getByText('taras')).toBeInTheDocument();
    expect(screen.getByText('olena')).toBeInTheDocument();
    expect(reply.querySelector('time')).toHaveAttribute('dateTime', '2026-11-01T15:30:00Z');
  });

  it('posts a comment with the author nickname and shows it after reload', async () => {
    // Trace: T-029
    apiClient.get
      .mockResolvedValueOnce(thread([]))
      .mockResolvedValueOnce(thread([comment('c1', 'My first comment', 0, [], 'admin')]));
    apiClient.post.mockResolvedValue({ data: {} });
    renderComments();
    await openThread();
    await screen.findByText(/Коментарів ще немає/);

    await userEvent.type(screen.getByRole('textbox', { name: 'Коментар' }), '  My first comment ');
    await userEvent.click(screen.getByRole('button', { name: 'Відправити' }));

    expect(apiClient.post).toHaveBeenCalledWith('/comments', {
      review_id: REVIEW_ID,
      user_id: CURRENT_USER_ID,
      author_name: 'admin',
      text: 'My first comment',
    });
    expect(await screen.findByText('My first comment')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Сховати коментарі/ })).toBeInTheDocument();
  });

  it('sends parent_id when replying to a comment', async () => {
    // Trace: T-029
    apiClient.get.mockResolvedValue(thread([comment('c1', 'Root comment')]));
    apiClient.post.mockResolvedValue({ data: {} });
    renderComments();
    await openThread();
    await screen.findByText('Root comment');

    await userEvent.click(screen.getByRole('button', { name: 'Відповісти' }));
    const replyBox = screen.getByPlaceholderText('Ваша відповідь...');
    await userEvent.type(replyBox, 'A reply');
    await userEvent.click(within(replyBox.closest('form')).getByRole('button', { name: 'Відправити' }));

    expect(apiClient.post).toHaveBeenCalledWith(
      '/comments',
      expect.objectContaining({ review_id: REVIEW_ID, text: 'A reply', parent_id: 'c1' })
    );
  });

  it('hides the reply button at the maximum depth', async () => {
    // Trace: T-029
    apiClient.get.mockResolvedValue(thread([comment('deep', 'Deepest comment', MAX_COMMENT_DEPTH)]));
    renderComments();
    await openThread();
    await screen.findByText('Deepest comment');

    expect(screen.queryByRole('button', { name: 'Відповісти' })).not.toBeInTheDocument();
  });

  it('blocks an empty comment with a message', async () => {
    // Trace: T-030
    apiClient.get.mockResolvedValue(thread([]));
    renderComments();
    await openThread();
    await screen.findByText(/Коментарів ще немає/);

    await userEvent.type(screen.getByRole('textbox', { name: 'Коментар' }), '   ');
    await userEvent.click(screen.getByRole('button', { name: 'Відправити' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Текст коментаря не може бути порожнім');
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('asks a guest to log in when they try to comment', async () => {
    // Trace: T-031
    apiClient.get.mockResolvedValue(thread([]));
    const openAuth = vi.fn();
    renderComments({ isLoggedIn: false, user: null, openAuth });
    await openThread();
    await screen.findByText(/Коментарів ще немає/);

    await userEvent.click(screen.getByRole('textbox', { name: 'Коментар' }));

    expect(openAuth).toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('Будь ласка, авторизуйтесь, щоб залишити коментар');

    await userEvent.click(screen.getByRole('button', { name: 'Відправити' }));
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('renders markup in comments as plain text', async () => {
    // Trace: T-032
    apiClient.get.mockResolvedValue(thread([comment('c1', '<img src=x onerror="alert(1)"><b>bold</b>')]));
    const { container } = renderComments();
    await openThread();

    expect(await screen.findByText('<img src=x onerror="alert(1)"><b>bold</b>')).toBeInTheDocument();
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('b')).toBeNull();
  });

  it('does not call the API for an invalid review id', async () => {
    // Trace: T-029
    const { container } = render(
      <ReviewComments reviewId="../../admin" isLoggedIn user={user} openAuth={vi.fn()} />
    );

    expect(container).toBeEmptyDOMElement();
    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it('shows a policy error returned by the server', async () => {
    // Trace: T-032
    apiClient.get.mockResolvedValue(thread([]));
    apiClient.post.mockRejectedValue({ response: { status: 400, data: { error: { code: 'POLICY_VIOLATION' } } } });
    renderComments();
    await openThread();
    await screen.findByText(/Коментарів ще немає/);

    await userEvent.type(screen.getByRole('textbox', { name: 'Коментар' }), '<script>alert(1)</script>');
    await userEvent.click(screen.getByRole('button', { name: 'Відправити' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('заборонений вміст');
  });

  it('asks to wait when the user posts too many comments', async () => {
    // Trace: T-051
    apiClient.get.mockResolvedValue(thread([]));
    apiClient.post.mockRejectedValue({ response: { status: 429, data: { error: { code: 'TOO_MANY_ATTEMPTS' } } } });
    renderComments();
    await openThread();
    await screen.findByText(/Коментарів ще немає/);

    await userEvent.type(screen.getByRole('textbox', { name: 'Коментар' }), 'Ще один коментар');
    await userEvent.click(screen.getByRole('button', { name: 'Відправити' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Забагато коментарів');
  });
});

describe('ReviewComments for a banned user (FR-009)', () => {
  beforeEach(() => {
    apiClient.get.mockReset();
    apiClient.post.mockReset();
  });

  it('shows the ban instead of the comment form', async () => {
    // Trace: T-036
    apiClient.get.mockResolvedValue(thread([]));
    renderComments({ user: { ...user, ban: { ban_type: 'permanent', ends_at: null, reason: null } } });

    await openThread();

    expect(await screen.findByText('Ваш акаунт заблоковано назавжди.')).toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });
});
