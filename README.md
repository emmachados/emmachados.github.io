# emmamachado.com

Bilingual academic site. English at the root, Spanish under `/es/`. `build.py`
renders static HTML from the YAML in `data/`. No JavaScript, analytics, cookies
or third-party requests.

## Building

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python build.py            # 16 pages into _site/
.venv/bin/python build.py --cv       # plus both CV PDFs; needs LuaLaTeX
cd _site && python3 -m http.server 8801
```

`--cv` renders `cv/cv.tex.j2` for both languages and copies the PDFs to the CV
pages. `--drafts` also builds entries flagged `hold: true`. A plain build skips
those and prints their ids.

The pages use absolute paths (`/static/...`). Serve `_site/` over HTTP.

## Layout

| Path | What it holds |
| --- | --- |
| `data/site.yml` | identity, profile links, the page-id to path map for both languages |
| `data/en.yml`, `data/es.yml` | every translatable string. Both files carry the same keys |
| `data/publications.yml` | 8 entries, structured fields |
| `data/talks.yml` | 27 entries |
| `data/awards.yml`, `data/courses.yml`, `data/education.yml`, `data/experience.yml`, `data/projects.yml`, `data/service.yml`, `data/software.yml`, `data/teaching.yml` | the remaining record |
| `templates/` | Jinja2, rendered once per language |
| `static/css/tokens.css` | every colour, font, space and motion token |
| `static/css/site.css` | the stylesheet |
| `static/css/fonts.css` | the `@font-face` rules for the woff2 files in `static/fonts/` |
| `cv/cv.tex.j2` | the CV, rendered from the same YAML |

## Deployment

Push to `main`. `.github/workflows/build.yml` installs the two Python packages
and TeX Live, runs `build.py --cv`, and publishes `_site/` through GitHub Pages.
`CNAME` carries the custom domain.

## Licensing

| Material | Licence |
| --- | --- |
| `build.py`, `templates/`, `cv/cv.tex.j2`, the stylesheets under `static/css/` | MIT |
| The prose of the site, the YAML corpus under `data/`, both CV PDFs | CC BY 4.0 |
| The slide decks under `static/teaching/` | CC BY-NC-SA 4.0 |
| Footer sprites under `static/img/`, from PMD Collab's SpriteCollab archive | CC BY-NC 4.0, characters trademarked by Nintendo, Creatures and Game Freak |
| Academicons glyphs inlined in `templates/partials/icons.html.j2` | SIL OFL 1.1 for the artwork, MIT for the code |
| Typefaces under `static/fonts/` and `cv/fonts/` | SIL OFL 1.1 |

`LICENSE` carries the MIT text and the same summary.
