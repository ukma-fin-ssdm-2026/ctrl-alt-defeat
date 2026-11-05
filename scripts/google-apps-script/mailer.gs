/**
 * «Після титрів» — email relay for account confirmation (FR-001).
 *
 * The site cannot send email directly from Render (SMTP ports are blocked on free services) and email
 * APIs need an own domain. This Google Apps Script web app receives a message over HTTPS and sends it
 * from the Gmail account that deployed it (about 100 emails per day for a personal account).
 *
 * Setup (see README, section 8):
 *   1. script.google.com -> New project -> paste this file.
 *   2. Project Settings -> Script Properties -> add MAILER_SECRET = a long random string.
 *   3. Deploy -> New deployment -> Web app; Execute as: Me; Who has access: Anyone -> Deploy, allow access.
 *   4. Put the Web app URL into GOOGLE_SCRIPT_URL and the same secret into GOOGLE_SCRIPT_SECRET (Render).
 *
 * Only requests with the secret are accepted, and only one plain recipient address per message.
 */

var EMAIL_PATTERN = /^[^\s@<>",;]+@[^\s@<>",;]+\.[^\s@<>",;]+$/;
var MAX_SUBJECT = 200;
var MAX_BODY = 20000;

function doPost(e) {
  try {
    var request = JSON.parse(e.postData.contents);
    var secret = PropertiesService.getScriptProperties().getProperty('MAILER_SECRET');

    if (!secret || request.secret !== secret) {
      return reply({ ok: false, error: 'unauthorized' });
    }
    if (typeof request.to !== 'string' || !EMAIL_PATTERN.test(request.to)) {
      return reply({ ok: false, error: 'invalid recipient' });
    }
    if (!request.subject || String(request.subject).length > MAX_SUBJECT) {
      return reply({ ok: false, error: 'invalid subject' });
    }
    if (!request.text || String(request.text).length > MAX_BODY || String(request.html || '').length > MAX_BODY) {
      return reply({ ok: false, error: 'invalid body' });
    }

    MailApp.sendEmail({
      to: request.to,
      subject: String(request.subject),
      body: String(request.text),
      htmlBody: request.html ? String(request.html) : undefined,
      name: request.name ? String(request.name).slice(0, 100) : 'Після титрів',
    });
    return reply({ ok: true });
  } catch (error) {
    return reply({ ok: false, error: 'bad request' });
  }
}

function reply(payload) {
  return ContentService.createTextOutput(JSON.stringify(payload)).setMimeType(ContentService.MimeType.JSON);
}
