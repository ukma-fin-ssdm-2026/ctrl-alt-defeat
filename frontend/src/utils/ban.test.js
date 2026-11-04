import { describe, expect, it } from 'vitest';
import { banStatusLabel, describeBan } from './ban';

describe('ban texts (FR-009)', () => {
  it('describes a permanent ban with the reason', () => {
    expect(describeBan({ ban_type: 'permanent', reason: 'Спам' })).toBe('Ваш акаунт заблоковано назавжди. Причина: Спам');
    expect(describeBan({ ban_type: 'permanent' }, 'EN')).toBe('Your account is permanently banned.');
  });

  it('describes a temporary ban with its end', () => {
    expect(describeBan({ ban_type: 'temporary', ends_at: '2026-11-12T10:00:00Z' }, 'EN')).toMatch(/^Your account is temporarily banned until 12\/11\/2026/);
  });

  it('labels the status in the admin list', () => {
    expect(banStatusLabel(null)).toBe('Активний');
    expect(banStatusLabel({ ban_type: 'permanent' }, 'EN')).toBe('Banned permanently');
    expect(describeBan(null)).toBe('');
  });
});
