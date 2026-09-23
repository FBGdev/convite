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

const familyFields = document.getElementById('family-fields');
const wifeCheckbox = document.getElementById('bring_wife');
const wifeField = document.getElementById('wife-field');
const wifeInput = document.getElementById('wife_name');
const addChildButton = document.getElementById('add-child');
const childRows = [...document.querySelectorAll('[data-child-row]')];
const activeChildren = new Set(childRows.filter(row => row.querySelector('input').value.trim()));

function updateFamilyFields() {
  if (!familyFields) return;
  const attending = document.querySelector('input[name="attending"]:checked')?.value === 'yes';
  familyFields.hidden = !attending;
  familyFields.disabled = !attending;
  wifeField.hidden = !wifeCheckbox.checked;
  wifeInput.disabled = !attending || !wifeCheckbox.checked;
  wifeInput.required = attending && wifeCheckbox.checked;
  let childNumber = 0;
  childRows.forEach(row => {
    const active = activeChildren.has(row);
    const input = row.querySelector('input');
    row.hidden = !active;
    input.disabled = !attending || !active;
    input.required = attending && active;
    const removeButton = row.querySelector('.remove-child');
    removeButton.hidden = !active;
    if (active) {
      childNumber += 1;
      row.querySelector('label').textContent = `Nome do filho ${childNumber}`;
      removeButton.setAttribute('aria-label', `Remover filho ${childNumber}`);
    }
  });
  addChildButton.hidden = !attending || activeChildren.size >= 2;
}

document.querySelectorAll('input[name="attending"]').forEach(input => {
  input.addEventListener('change', updateFamilyFields);
});
wifeCheckbox?.addEventListener('change', updateFamilyFields);
addChildButton?.addEventListener('click', () => {
  const row = childRows.find(item => !activeChildren.has(item));
  if (!row) return;
  activeChildren.add(row);
  updateFamilyFields();
  row.querySelector('input').focus();
});
childRows.forEach(row => {
  row.querySelector('.remove-child').addEventListener('click', () => {
    row.querySelector('input').value = '';
    activeChildren.delete(row);
    updateFamilyFields();
    addChildButton.focus();
  });
});
updateFamilyFields();
