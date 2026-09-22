const attendingInputs = document.querySelectorAll('input[name="attending"]');
const companionsField = document.getElementById('companions-field');
const companionsSelect = document.getElementById('companions');

function updateCompanions() {
  if (!companionsField) return;
  const yes = document.querySelector('input[name="attending"][value="yes"]')?.checked;
  companionsField.hidden = !yes;
  if (!yes && companionsSelect) companionsSelect.value = '0';
}

attendingInputs.forEach(input => input.addEventListener('change', updateCompanions));
updateCompanions();
