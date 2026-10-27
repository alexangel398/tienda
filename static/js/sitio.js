document.addEventListener("DOMContentLoaded", () => {
    const boton = document.querySelector("[data-menu-boton]");
    const cabecera = document.querySelector(".cabecera");
    if (boton && cabecera) {
        boton.addEventListener("click", () => {
            const abierto = cabecera.classList.toggle("menu-abierto");
            boton.setAttribute("aria-expanded", String(abierto));
        });
    }

    document.querySelectorAll("[data-autoenviar]").forEach((campo) => {
        campo.addEventListener("change", () => campo.form.submit());
    });
});