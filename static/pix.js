const copyPixButton = document.getElementById('copy-pix');

copyPixButton?.addEventListener('click', async () => {
  const pixKey = document.getElementById('pix-key');
  const status = document.getElementById('copy-pix-status');
  try {
    await navigator.clipboard.writeText(pixKey.textContent.trim());
    status.textContent = 'Chave Pix copiada!';
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(pixKey);
    selection.removeAllRanges();
    selection.addRange(range);
    status.textContent = 'Chave selecionada. Copie e cole no aplicativo do banco.';
  }
});
