import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import AuthModal from './AuthModal';

vi.mock('../api/client', () => ({ default: { post: vi.fn(), get: vi.fn() } }));

describe('AuthModal notice (FR-005)', () => {
  it('shows why a guest was asked to log in', () => {
    // Trace: T-001
    render(<AuthModal close={() => {}} onLogin={vi.fn()} notice="Будь ласка, авторизуйтесь для використання цієї функції" />);

    expect(screen.getByRole('status')).toHaveTextContent('Будь ласка, авторизуйтесь для використання цієї функції');
  });

  it('shows no notice by default', () => {
    // Trace: T-001
    render(<AuthModal close={() => {}} onLogin={vi.fn()} />);

    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});
