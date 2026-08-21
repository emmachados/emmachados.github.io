#!/usr/bin/env python3
import argparse
import datetime as dt
import pathlib
import re
import shutil
import subprocess
import sys

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "data"
OUT = ROOT / "_site"

PRELOAD_FONTS = ["bodoni-moda-normal-400_900-latin.woff2",
                 "plus-jakarta-sans-normal-300_800-latin.woff2"]

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
}


def load(name):
    return yaml.safe_load((DATA / f"{name}.yml").read_text(encoding="utf-8"))


OPTIONAL = {
    "publications": ["doi", "url", "volume", "issue", "pages", "container",
                     "publisher", "indicators", "status", "featured", "hold",
                     "outreach", "editors",
                     "lang"],
    "talks": ["date_end", "panel", "award", "hold"],
    "teaching": ["course", "programme", "module", "detail", "hours", "dates",
                 "materials"],
    "service": ["detail", "hold", "featured", "convened_with", "panel_title",
                "url"],
    "awards": ["detail", "of", "org"],
    "experience": ["detail", "place", "end"],
    "projects": ["funder", "contract", "scope", "pi",
                 "year_start", "year_end"],
    "education": ["detail", "work_label", "work_title"],
}


def with_defaults(items, kind):
    for it in items:
        for k in OPTIONAL[kind]:
            it.setdefault(k, None)
    return items


def authors(names, lang):

    amp = "&"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]}, {amp} {names[1]}"
    return ", ".join(names[:-1]) + f", {amp} {names[-1]}"


def initialled(names):

    out = []
    for n in names:
        surname, _, initials = n.partition(",")
        out.append(f"{initials.strip()} {surname.strip()}".strip())
    if len(out) == 1:
        return out[0]
    if len(out) == 2:
        return f"{out[0]} & {out[1]}"
    return ", ".join(out[:-1]) + f", & {out[-1]}"


def date_range(start, end, lang):
    m = MONTHS[lang]
    if not end or end == start:
        d = f"{start.day} {m[start.month - 1]} {start.year}"
        return d if lang == "en" else f"{start.day} de {m[start.month - 1]} de {start.year}"
    if start.year == end.year and start.month == end.month:
        if lang == "en":
            return f"{start.day}-{end.day} {m[start.month - 1]} {start.year}"
        return f"{start.day}-{end.day} de {m[start.month - 1]} de {start.year}"
    if start.year == end.year:
        if lang == "en":
            return f"{start.day} {m[start.month - 1]} - {end.day} {m[end.month - 1]} {start.year}"
        return (f"{start.day} de {m[start.month - 1]} a {end.day} "
                f"de {m[end.month - 1]} de {start.year}")
    return f"{start.isoformat()} / {end.isoformat()}"


def month_span(start, end, lang, present):
\

    def one(v):
        y, m = (v.year, v.month) if hasattr(v, "year") else (int(str(v)[:4]), int(str(v)[5:7]))
        name = MONTHS[lang][m - 1]
        return f"{name} {y}" if lang == "en" else f"{name} de {y}"
    if end is None:
        return f"{one(start)} - {present}"
    if one(start) == one(end):
        return one(start)
    return f"{one(start)} - {one(end)}"


def year_span(start, end):
\

    def y(v):
        return v.year if hasattr(v, "year") else int(str(v)[:4])
    if end is None:
        return f"{y(start)}\u2013"
    if y(start) == y(end):
        return str(y(start))
    return f"{y(start)}\u2013{y(end)}"


def month_span_short(start, end, lang, present):

    def one(v):
        y, m = (v.year, v.month) if hasattr(v, "year") else (int(str(v)[:4]), int(str(v)[5:7]))
        return f"{MONTHS[lang][m - 1][:3].rstrip('.')}. {y}"
    if end is None:
        return f"{one(start)}-{present}"
    if one(start) == one(end):
        return one(start)
    return f"{one(start)}-{one(end)}"


def apa(pub, t, lang, emphasise_title=False):
\
\

    a = authors(pub["authors"], lang)
    year = pub["year"]
    if pub.get("status") in ("forthcoming", "in_press"):
        year = t["publications"]["status"][pub["status"]].lower()


    title = f"<em>{pub['title']}</em>" if pub["type"] in ("edited", "book") else pub["title"]
    if emphasise_title:
        url = doi_url(pub)
        inner = f'<a href="{url}">{title}</a>' if url else title
        title = f'<strong class="entry__t">{inner}</strong>'
    if pub["type"] in ("edited", "book"):
        return f"{a} ({year}). {title}. {pub['publisher']}."

    stop = "" if pub["title"].rstrip().endswith(("?", "!")) else "."
    bits = [f"{a} ({year}). {title}{stop}"]
    if pub["type"] == "chapter":
        pages = f" (pp. {pub['pages']})" if pub.get("pages") else ""

        eds = pub.get("editors") or []
        if eds:
            names = initialled(eds)
            label = t["publications"]["ed" if len(eds) == 1 else "eds"]
            ed = f"{names} ({label}), "
        else:
            ed = ""
        bits.append(f"{t['publications']['in']} {ed}<em>{pub['container']}</em>{pages}. {pub['publisher']}.")
    else:
        vol = f", <em>{pub['volume']}</em>" if pub.get("volume") else ""
        iss = f"({pub['issue']})" if pub.get("issue") else ""
        if pub.get("issue") and not pub.get("volume"):
            iss = f", {iss}"
        pages = f", {pub['pages']}" if pub.get("pages") else ""
        bits.append(f"<em>{pub['venue']}</em>{vol}{iss}{pages}.")
    return " ".join(bits)


def doi_url(pub):
\
\

    if pub.get("doi"):
        return f"https://doi.org/{pub['doi']}"
    return pub.get("url") or None


def context(lang, site, copy, data, preload=()):
    pages = site["pages"]

    def path_for(page_id, in_lang=None):
        return pages[page_id][in_lang or lang]

    return dict(
        lang=lang,
        other_lang="es" if lang == "en" else "en",
        site=site,
        photo=(site.get("photo") or {}).get(lang),
        t=copy[lang],
        path_for=path_for,
        nav=[(pid, meta) for pid, meta in pages.items() if meta.get("nav")],
        apa=lambda p: apa(p, copy[lang], lang, emphasise_title=True),
        apa_plain=lambda p: apa(p, copy[lang], lang),
        doi_url=doi_url,
        date_range=lambda s, e: date_range(s, e, lang),
        month_span=lambda s, e: month_span(s, e, lang, copy[lang]["cv"]["present"]),
        month_span_short=lambda s, e: month_span_short(s, e, lang, copy[lang]["cv"]["present"]),
        year_span=year_span,
        authors=lambda n: authors(n, lang),
        build_date=dt.date.today().isoformat(),
        preload_fonts=preload,
        **data,
    )


def group_by_year(items, key):
    out = {}
    for it in items:
        out.setdefault(key(it), []).append(it)
    return sorted(out.items(), key=lambda kv: kv[0], reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv", action="store_true", help="also compile the CV PDF")
    ap.add_argument("--drafts", action="store_true",
                    help="include entries held back by a hold: true flag")
    args = ap.parse_args()

    site = load("site")
    copy = {"en": load("en"), "es": load("es")}


    for lang_key, rel in list((site.get("photo") or {}).items()):
        if not (ROOT / "static" / rel).exists():
            print(f"  no portrait at static/{rel} - omitting the {lang_key} figure")
            site["photo"][lang_key] = None

    pubs = with_defaults(load("publications"), "publications")
    talks = with_defaults(load("talks"), "talks")
    if not args.drafts:
        held = [p["id"] for p in pubs + talks if p.get("hold")]
        if held:
            print(f"  holding back {len(held)} unverified entries: {', '.join(held)}")
        pubs = [p for p in pubs if not p.get("hold")]
        talks = [p for p in talks if not p.get("hold")]

    education = with_defaults(load("education")["entries"], "education")
    projects = load("projects")
    with_defaults(projects["projects"], "projects")

    pubs = sorted(pubs, key=lambda p: p["year"], reverse=True)
    talks = sorted(talks, key=lambda t: t["date_start"], reverse=True)
    data = dict(
        publications=pubs,
        publications_by_year=group_by_year(
            [p for p in pubs if not p.get("outreach")], lambda p: p["year"]),
        outreach_pubs=[p for p in pubs if p.get("outreach")],
        featured=[p for p in pubs if p.get("featured") and not p.get("outreach")
                  and p.get("status") not in ("forthcoming", "in_press")][:5],
        talks=talks,
        talks_by_year=group_by_year(talks, lambda t: t["date_start"].year),
        teaching=with_defaults(load("teaching"), "teaching"),
        service=with_defaults(load("service"), "service"),
        service_kinds=["chair", "committee", "panel", "review", "corpus", "outreach"],
        projects=projects,

        project_scopes=["international", "own", "contract"],
        software=load("software"),
        courses=load("courses"),
        awards=with_defaults(load("awards"), "awards"),
        experience=with_defaults(load("experience"), "experience"),
        education=education,

        sprites={"home": "idle", "publications": "walk", "talks": "charge",
                 "teaching": "rotate", "service": "withdraw", "cv": "sleep",
                 "software": "double", "course_mq": "idle"},
    )

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=StrictUndefined,
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    written = []
    for lang in ("en", "es"):
        ctx = context(lang, site, copy, data, PRELOAD_FONTS)
        for page_id, meta in site["pages"].items():
            tpl = env.get_template(f"{page_id}.html.j2")
            html = tpl.render(page=page_id, noindex=meta.get("noindex", False),
                              **ctx)
            rel = meta[lang].strip("/")
            target = OUT / rel / "index.html" if rel else OUT / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(html, encoding="utf-8")
            written.append(target.relative_to(OUT))


    missing = [f"{p}-{a}.png" for a in set(data["sprites"].values())
               for p in ("sprite", "trubbish")
               if not (ROOT / "static" / "img" / f"{p}-{a}.png").exists()]
    if missing:
        sys.exit("missing sprite strips: " + ", ".join(sorted(missing)))

    shutil.copytree(ROOT / "static", OUT / "static")
    shutil.copy(ROOT / "CNAME", OUT / "CNAME")


    for lang in ("en", "es"):
        made = ROOT / "cv" / "build" / f"cv-{lang}.pdf"
        if made.exists():
            dest = OUT / site["pages"]["cv"][lang].strip("/") / f"machado-de-souza-cv-{lang}.pdf"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(made, dest)


    base = site["base_url"]
    urls = [f"{base}{m[l]}" for pid, m in site["pages"].items()
            if not m.get("noindex") for l in ("en", "es")]
    body = "".join(f"  <url><loc>{u}</loc></url>\n" for u in sorted(urls))
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}</urlset>\n", encoding="utf-8")
    noindexed = [m[l] for pid, m in site["pages"].items()
                 if m.get("noindex") for l in ("en", "es")]
    disallow = "".join(f"Disallow: {p}\n" for p in sorted(noindexed))
    (OUT / "robots.txt").write_text(
        f"User-agent: *\n{disallow}Sitemap: {base}/sitemap.xml\n", encoding="utf-8")

    print(f"  {len(written)} pages -> {OUT}")

    if args.cv:
        compile_cv(site, copy, data)


def compile_cv(site, copy, data):
    tex_tpl = Environment(
        loader=FileSystemLoader(ROOT / "cv"),
        undefined=StrictUndefined,
        autoescape=False,
        block_start_string="<%", block_end_string="%>",
        variable_start_string="<<", variable_end_string=">>",
        comment_start_string="<#", comment_end_string="#>",
        trim_blocks=True, lstrip_blocks=True,
    ).get_template("cv.tex.j2")
    build = ROOT / "cv" / "build"
    build.mkdir(exist_ok=True)
    for lang in ("en", "es"):
        ctx = context(lang, site, copy, data)
        ctx["apa"] = lambda p, l=lang: html_to_tex(apa(p, copy[l], l))
        ctx["tex"] = tex_escape
        tex = tex_tpl.render(**ctx)
        src = build / f"cv-{lang}.tex"
        src.write_text(tex, encoding="utf-8")

        r = subprocess.run(
            [lualatex(), "-interaction=nonstopmode",
             "-halt-on-error", "-output-directory=build", f"build/cv-{lang}.tex"],
            cwd=ROOT / "cv", capture_output=True, text=True)
        if r.returncode != 0:
            tail = "\n".join(r.stdout.splitlines()[-30:])
            print(f"  lualatex failed for {lang}:\n{tail}", file=sys.stderr)
            sys.exit(1)
        pdf = build / f"cv-{lang}.pdf"
        dest = OUT / site["pages"]["cv"][lang].strip("/") / f"machado-de-souza-cv-{lang}.pdf"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdf, dest)
        print(f"  CV {lang} -> {dest.relative_to(OUT)}")


def lualatex():

    found = shutil.which("lualatex") or "/Library/TeX/texbin/lualatex"
    if not pathlib.Path(found).exists():
        sys.exit("lualatex not found; install MacTeX or texlive-luatex")
    return found


def html_to_tex(s):
\
\

    out = []
    for i, chunk in enumerate(re.split(r"</?em>", s)):
        out.append(f"\\emph{{{tex_escape(chunk)}}}" if i % 2 else tex_escape(chunk))
    return "".join(out)


def tex_escape(s):
    s = str(s)
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
                 ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]:
        s = s.replace(a, b)
    return s


if __name__ == "__main__":
    main()
