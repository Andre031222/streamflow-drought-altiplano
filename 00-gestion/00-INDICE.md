# Gestión del proyecto — índice

Esta carpeta concentra la **documentación de gestión** del paper (decisiones, plan de trabajo y bitácora de avance). Antes estos archivos `.md` estaban sueltos en la raíz y mezclaban el esquema numerado `01`…`05` con varios `00-*`. Ahora la raíz queda limpia: un solo `00-gestion/` junto a las carpetas de contenido científico.

## Contenido de `00-gestion/`

| Archivo | Descripción |
| --- | --- |
| `00-INDICE.md` | Este índice: layout del repositorio y convenciones. |
| `01-decision.md` | Decisiones de tema, venue, autores y hardware. |
| `02-plan-4h.md` | Plan de trabajo de la sesión / checklist de hitos. |
| `03-avance-bitacora.md` | Bitácora técnica bilingüe (objetivos, métodos, resultados reales, citas, pendiente de envío). |

## Layout numerado del repositorio

| Ruta | Rol |
| --- | --- |
| `00-gestion/` | Gestión, bitácora y decisiones (no entra al PDF). |
| `01-articulo/` | Manuscrito Springer (`manuscrito/`), abstract, borrador y PDF de trabajo. |
| `02-datos/` | Datos crudos, procesados e inventario de fuentes. |
| `03-codigo/` | Pipeline Python público; `local/` queda **gitignore** (QGIS / Cartopy de taller). |
| `04-resultados/` | Figuras (PNG 600 dpi + PDF) y tablas de métricas. |
| `05-plantilla-springer/` | Plantilla y guidelines **oficiales Springer** (vendor). |

### Por qué `05-plantilla-springer/` permanece en la raíz

La plantilla Springer no se anida bajo `01-articulo/` a propósito: (1) el manuscrito activo ya tiene `svmult.cls`, estilos y `bst` copiados en `01-articulo/manuscrito/`; (2) `.gitignore` excluye zips y PDFs pesados de vendor bajo la ruta `05-plantilla-springer/`; (3) moverla rompería referencias del plan y del ignore sin beneficio para la compilación. Se deja como carpeta **numerada de referencia**, separada del manuscrito editable.

### Compilación LaTeX (sin cambios de ruta)

- Fuentes: `01-articulo/manuscrito/caudal-sequia-altiplano.tex` (+ `cifras.tex`).
- Figuras: symlink `01-articulo/manuscrito/figuras` → `../../04-resultados/figuras`.
- El `.tex` canónico usa rutas relativas `figuras/...`; `manuscript.tex` (borrador) también incluye `\graphicspath` hacia `../../04-resultados/figuras/`.
- Código: `03-codigo/config.py` apunta a `02-datos/` y `04-resultados/` desde la raíz del repo.

```bash
cd 01-articulo/manuscrito
pdflatex caudal-sequia-altiplano.tex
pdflatex caudal-sequia-altiplano.tex
```

### Convención

- Prefijo numérico = orden de lectura / pipeline (`00` gestión → `05` plantilla vendor).
- Documentos de proceso solo en `00-gestion/`; el README de la raíz describe el layout público y la reproducción.

## Destino de envío (venue)

- **Conferencia:** ICICCDS 2027
- **Portal CMT:** https://cmt3.research.microsoft.com/ICICCDS2027
- **PDF a enviar:** `01-articulo/caudal-sequia-altiplano.pdf`
- **Autores:** Richar Andre Vilca-Solorzano, Renato Quispe-Vargas y Dina Maribel Yana-Yucra (UNAP–FINESI)
- **Estado:** ACEPTADO (Paper ID 51, correo CMT del 18 Oct 2026). Actas Springer, serie ADIC (Scopus). Pendiente: CRC en formato Springer + registro antes del 30 Oct 2026, enviar ambos a iciccds.congress@gmail.com y llenar el formulario post-pago.
- **Nombre oficial (CMT):** International Conference on Intelligent Computing, Communication and Data Science. ICCCDS (Mumbai) es otro congreso distinto.

