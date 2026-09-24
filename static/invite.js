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

const companionFields = document.getElementById('companion-fields');
const addCompanionButton = document.getElementById('add-companion');
const companionRows = [...document.querySelectorAll('[data-companion-row]')];
const activeCompanions = new Set(companionRows.filter(row => row.querySelector('input').value.trim()));

function updateCompanionFields() {
  if (!companionFields) return;
  const attending = document.querySelector('input[name="attending"]:checked')?.value === 'yes';
  companionFields.hidden = !attending;
  companionFields.disabled = !attending;
  let companionNumber = 0;
  companionRows.forEach(row => {
    const active = activeCompanions.has(row);
    const input = row.querySelector('input');
    row.hidden = !active;
    input.disabled = !attending || !active;
    input.required = attending && active;
    const removeButton = row.querySelector('.remove-companion');
    removeButton.hidden = !active;
    if (active) {
      companionNumber += 1;
      row.querySelector('label').textContent = `Nome do acompanhante ${companionNumber}`;
      removeButton.setAttribute('aria-label', `Remover acompanhante ${companionNumber}`);
    }
  });
  addCompanionButton.hidden = !attending || activeCompanions.size >= 6;
}

document.querySelectorAll('input[name="attending"]').forEach(input => {
  input.addEventListener('change', updateCompanionFields);
});
addCompanionButton?.addEventListener('click', () => {
  const row = companionRows.find(item => !activeCompanions.has(item));
  if (!row) return;
  activeCompanions.add(row);
  updateCompanionFields();
  row.querySelector('input').focus();
});
companionRows.forEach(row => {
  row.querySelector('.remove-companion').addEventListener('click', () => {
    row.querySelector('input').value = '';
    activeCompanions.delete(row);
    updateCompanionFields();
    addCompanionButton.focus();
  });
});
updateCompanionFields();
