// Pequeño script UX para botón de envío
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("[data-auth-form]");
  const submit = form?.querySelector("button[type='submit']");

  if (form && submit) {
    form.addEventListener("submit", () => {
      submit.disabled = true;
      submit.textContent = "Guardando…";
    });
  }
});
