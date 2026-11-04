// FR-009: human-readable text of the ban in force (type, period, reason from the administrator)

const formatDate = (iso, isUkr) =>
  new Date(iso).toLocaleString(isUkr ? 'uk-UA' : 'en-GB', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

export function describeBan(ban, language = 'UKR') {
  if (!ban) return '';
  const isUkr = language === 'UKR';
  const period =
    ban.ban_type === 'permanent' || !ban.ends_at
      ? (isUkr ? 'Ваш акаунт заблоковано назавжди.' : 'Your account is permanently banned.')
      : (isUkr
        ? `Ваш акаунт тимчасово заблоковано до ${formatDate(ban.ends_at, isUkr)}.`
        : `Your account is temporarily banned until ${formatDate(ban.ends_at, isUkr)}.`);
  const reason = ban.reason ? (isUkr ? ` Причина: ${ban.reason}` : ` Reason: ${ban.reason}`) : '';
  return period + reason;
}

export function banStatusLabel(ban, language = 'UKR') {
  const isUkr = language === 'UKR';
  if (!ban) return isUkr ? 'Активний' : 'Active';
  if (ban.ban_type === 'permanent' || !ban.ends_at) return isUkr ? 'Заблоковано назавжди' : 'Banned permanently';
  return isUkr ? `Заблоковано до ${formatDate(ban.ends_at, isUkr)}` : `Banned until ${formatDate(ban.ends_at, isUkr)}`;
}
