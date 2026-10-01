# Manuscript sources

Main file: **`caudal-sequia-altiplano.tex`**. It inputs `results.tex` and `backmatter.tex`, plus the auto-generated `cifras.tex` and `tab_*.tex` files, which are written by `03-codigo/make_cifras.py`. Do not edit those by hand.

Compile with `pdflatex`, then `bibtex`, then `pdflatex` twice. Figures come from `figuras/`, a symlink to `../../04-resultados/figuras`.
