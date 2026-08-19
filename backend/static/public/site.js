(() => {
    const form = document.querySelector("[data-lookup-form]");
    const input = document.querySelector("#account-number");

    if (input) {
        input.addEventListener("input", () => {
            input.value = input.value.replace(/[^\d\s\-–—−]/g, "");
            input.removeAttribute("aria-invalid");
        });
    }

    if (form) {
        form.addEventListener("submit", (event) => {
            if (!input || !input.value.trim()) {
                event.preventDefault();
                input?.setAttribute("aria-invalid", "true");
                input?.focus();
                return;
            }
            const button = form.querySelector("button[type='submit']");
            const label = button?.querySelector(".button-label");
            if (button) {
                button.disabled = true;
                button.classList.add("is-loading");
            }
            if (label) label.textContent = "Проверяем счёт";
        });
    }

    if (document.querySelector(".form-error") && input) {
        input.focus();
    }

    document.querySelector("[data-print-button]")?.addEventListener("click", () => window.print());

    const result = document.querySelector("[data-account-result]");
    if (result && window.location.hash !== "#account-result") {
        result.focus({ preventScroll: true });
        const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        result.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    }
})();
