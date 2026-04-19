(() => {
  const form = document.querySelector("[data-input-form]");
  if (!form) {
    return;
  }

  const inputs = [...form.querySelectorAll("[data-nav-input]")];
  if (!inputs.length) {
    return;
  }

  inputs.forEach((input, index) => {
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") {
        return;
      }

      const nextInput = inputs[index + 1];
      if (nextInput) {
        event.preventDefault();
        nextInput.focus();
        nextInput.select();
        return;
      }

      form.requestSubmit();
    });
  });
})();
