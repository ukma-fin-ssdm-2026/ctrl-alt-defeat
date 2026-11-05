import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AchievementToast, { ACHIEVEMENT_TOAST_MS } from './AchievementToast';

const badge = { id: 'first-review', icon: '🖊️', titleUkr: 'Перше слово', titleEn: 'First Word', descUkr: 'Напишіть свою першу рецензію', descEn: 'Write your first review' };

describe('AchievementToast', () => {
  afterEach(() => vi.useRealTimers());

  it('renders nothing without a badge', () => {
    const { container } = render(<AchievementToast badge={null} onView={() => {}} onClose={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('announces the badge and opens it on "View"', async () => {
    const onView = vi.fn();
    const onClose = vi.fn();
    render(<AchievementToast badge={badge} pending={2} onView={onView} onClose={onClose} />);

    expect(screen.getByRole('status')).toHaveTextContent('Нова нагорода!');
    expect(screen.getByText('Перше слово')).toBeInTheDocument();
    expect(screen.getByText('і ще 2')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Переглянути' }));
    expect(onView).toHaveBeenCalledWith(badge);

    await userEvent.click(screen.getByRole('button', { name: 'Закрити' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('speaks English and hides itself after a while', () => {
    vi.useFakeTimers();
    const onClose = vi.fn();
    render(<AchievementToast badge={badge} language="EN" onView={() => {}} onClose={onClose} />);

    expect(screen.getByText('First Word')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View' })).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(ACHIEVEMENT_TOAST_MS));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe('AchievementToast for a rank', () => {
  it('says it is a new rank', () => {
    render(<AchievementToast badge={{ ...badge, kind: 'rank', id: 'rank-fan', titleUkr: 'Кінолюб' }} onView={() => {}} onClose={() => {}} />);
    expect(screen.getByRole('status')).toHaveTextContent('Новий ранг!');
  });
});
