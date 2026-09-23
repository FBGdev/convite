const rsvpDialog = document.getElementById('rsvp-dialog');
let rsvpTrigger = null;

function openRsvp(trigger = null) {
  if (!rsvpDialog || rsvpDialog.open) return;
  rsvpTrigger = trigger;
  rsvpDialog.showModal();
  document.body.classList.add('rsvp-modal-open');
  const focusTarget = rsvpDialog.querySelector('.form-error') || document.getElementById('full_name');
  focusTarget?.focus();
}

document.querySelectorAll('[data-open-rsvp]').forEach(trigger => {
  trigger.addEventListener('click', event => {
    event.preventDefault();
    openRsvp(trigger);
  });
});

document.querySelector('[data-close-rsvp]')?.addEventListener('click', () => rsvpDialog?.close());
rsvpDialog?.addEventListener('close', () => {
  document.body.classList.remove('rsvp-modal-open');
  rsvpTrigger?.focus();
  rsvpTrigger = null;
});

if (rsvpDialog?.dataset.openOnLoad === 'true') openRsvp();

const phoneInput = document.getElementById('phone');

function maskBrazilianPhone(value) {
  let digits = value.replace(/\D/g, '');
  if (digits.startsWith('55') && digits.length > 11) digits = digits.slice(2);
  digits = digits.slice(0, 11);
  if (digits.length <= 2) return digits ? `(${digits}` : '';
  const areaCode = digits.slice(0, 2);
  const number = digits.slice(2);
  if (number.length <= 4) return `(${areaCode}) ${number}`;
  return `(${areaCode}) ${number.slice(0, -4)}-${number.slice(-4)}`;
}

phoneInput?.addEventListener('input', () => {
  const before = phoneInput.value.slice(0, phoneInput.selectionStart ?? phoneInput.value.length);
  const digitsBefore = before.replace(/\D/g, '').length;
  const formatted = maskBrazilianPhone(phoneInput.value);
  phoneInput.value = formatted;
  let cursor = 0;
  let seen = 0;
  while (cursor < formatted.length && seen < digitsBefore) {
    if (/\d/.test(formatted[cursor])) seen += 1;
    cursor += 1;
  }
  phoneInput.setSelectionRange(cursor, cursor);
});

if (phoneInput?.value) phoneInput.value = maskBrazilianPhone(phoneInput.value);
