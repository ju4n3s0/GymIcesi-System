// Toggle de visibilidad de contraseña + UX mínimos
(function () {
  const pwd = document.querySelector('#id_password') || document.querySelector('input[type="password"]');
  const toggle = document.querySelector('[data-toggle="password"]');
  const form = document.querySelector('[data-auth-form]');
  const submit = form ? form.querySelector('button[type="submit"]') : null;

  if (toggle && pwd) {
    toggle.addEventListener('click', () => {
      const type = pwd.getAttribute('type') === 'password' ? 'text' : 'password';
      pwd.setAttribute('type', type);
      toggle.setAttribute('aria-pressed', type === 'text');
    });
  }

  if (form && submit) {
    form.addEventListener('submit', () => {
      submit.disabled = true;
      submit.dataset.loading = 'true';
      submit.textContent = 'Ingresando…';
    });
  }
})();
