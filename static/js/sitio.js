document.addEventListener("DOMContentLoaded", () => {
    const cabecera = document.querySelector(".cabecera");
    const botonMenu = document.querySelector("[data-menu-boton]");
    const modal = document.querySelector("[data-modal]");

    if (cabecera && botonMenu) {
        botonMenu.addEventListener("click", () => {
            const abierto = cabecera.classList.toggle("menu-abierto");
            botonMenu.setAttribute("aria-expanded", String(abierto));
        });
    }

    // Los campos con data-autoenviar envían su formulario al cambiar.
    document.addEventListener("change", (e) => {
        if (e.target.matches("[data-autoenviar]")) e.target.form.submit();
    });

    // Galería: actualiza puntos y estado de las flechas
    const actualizarGaleria = (pista) => {
        const galeria = pista.closest("[data-galeria]");
        if (!galeria) return;
        const slides = pista.querySelectorAll(".visor-slide");
        if (slides.length === 0) return;
        
        const anchoSlide = slides[0].clientWidth;
        const actual = Math.round(pista.scrollLeft / anchoSlide);

        galeria.querySelectorAll("[data-punto]").forEach((punto, i) => {
            punto.classList.toggle("activo", i === actual);
        });

        const anterior = galeria.querySelector("[data-anterior]");
        const siguiente = galeria.querySelector("[data-siguiente]");
        if (anterior) anterior.disabled = actual <= 0;
        if (siguiente) siguiente.disabled = actual >= slides.length - 1;
    };

    document.addEventListener("scroll", (e) => {
        if (e.target && e.target.matches && e.target.matches("[data-pista]")) {
            actualizarGaleria(e.target);
        }
    }, true);

    document.addEventListener("click", async (e) => {
        // Selector de cantidad: − y +
        const paso = e.target.closest("[data-cantidad-menos], [data-cantidad-mas]");
        if (paso) {
            const campo = paso.closest("[data-selector]").querySelector("input");
            const delta = paso.hasAttribute("data-cantidad-mas") ? 1 : -1;
            const minimo = Number(campo.min || 0);
            const maximo = campo.max ? Number(campo.max) : Infinity;
            const nuevo = Math.min(maximo, Math.max(minimo, Number(campo.value || 0) + delta));
            if (nuevo !== Number(campo.value)) {
                campo.value = nuevo;
                campo.dispatchEvent(new Event("change", { bubbles: true }));
            }
            return;
        }

        // Galería: flechas y puntos mueven el visor de forma directa
        const control = e.target.closest("[data-anterior], [data-siguiente], [data-punto]");
        if (control) {
            const galeria = control.closest("[data-galeria]");
            if (!galeria) return;
            const pista = galeria.querySelector("[data-pista]");
            if (!pista) return;

            const slides = pista.querySelectorAll(".visor-slide");
            if (slides.length === 0) return;
            const anchoSlide = slides[0].clientWidth;
            const actual = Math.round(pista.scrollLeft / anchoSlide);
            let destino = actual;

            if (control.hasAttribute("data-punto")) {
                destino = Number(control.dataset.punto);
            } else if (control.hasAttribute("data-siguiente")) {
                destino = actual + 1;
            } else if (control.hasAttribute("data-anterior")) {
                destino = actual - 1;
            }

            // Asegurar límites
            destino = Math.max(0, Math.min(destino, slides.length - 1));

            pista.scrollTo({ left: destino * anchoSlide, behavior: "smooth" });
            
            // Actualizar visualmente de inmediato
            setTimeout(() => actualizarGaleria(pista), 250);
            return;
        }

        // Vista rápida: carga la ficha dentro de la ventana
        const abrir = e.target.closest("[data-vista-rapida]");
        if (abrir && modal) {
            const contenido = modal.querySelector("[data-modal-contenido]");
            contenido.innerHTML = '<p class="texto-suave">Cargando...</p>';
            modal.showModal();
            try {
                const respuesta = await fetch(abrir.dataset.vistaRapida);
                if (!respuesta.ok) throw new Error("Respuesta inválida");
                contenido.innerHTML = await respuesta.text();
                contenido.querySelectorAll('input[name="next"]').forEach((campo) => {
                    campo.value = location.pathname + location.search;
                });
            } catch {
                contenido.innerHTML = "<p>No se pudo cargar el producto.</p>";
            }
            return;
        }

        // Cerrar la ventana: botón o clic fuera
        if (modal && (e.target.closest("[data-modal-cerrar]") || e.target === modal)) {
            modal.close();
            return;
        }

        // Compartir: menú del sistema o copiar el enlace
        const compartir = e.target.closest("[data-compartir]");
        if (compartir) {
            const { url, titulo } = compartir.dataset;
            try {
                if (navigator.share) {
                    await navigator.share({ title: titulo, url });
                } else {
                    await navigator.clipboard.writeText(url);
                    const texto = compartir.querySelector("span");
                    const original = texto.textContent;
                    texto.textContent = "Enlace copiado";
                    setTimeout(() => { texto.textContent = original; }, 2000);
                }
            } catch {
                /* el usuario canceló o el navegador no lo permite */
            }
        }
    });
});