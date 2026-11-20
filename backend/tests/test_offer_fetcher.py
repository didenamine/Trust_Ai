import json

import httpx
import pytest

from app.services import offer_fetcher

PUBLIC_IP = "93.184.216.34"
OFFER_URL = "https://jobs.example.com/offres/42"

OFFER_HTML = """
<html><head><title>Développeur Python</title></head><body>
<nav><a href="/">Accueil</a></nav>
<article>
<h1>Développeur Python backend (H/F)</h1>
<p>Rejoignez notre équipe pour concevoir des API REST avec FastAPI et PostgreSQL. Vous
travaillerez avec des développeurs front et des data scientists dans un environnement agile.</p>
<p>Profil recherché : 3 ans d'expérience minimum en Python, bonne connaissance de Docker,
des tests automatisés et de Git. Vous aimez écrire du code propre et le partager.</p>
<p>Nous offrons un contrat CDI, du télétravail partiel, une mutuelle prise en charge et un
budget formation annuel pour progresser sur les technologies de votre choix.</p>
</article>
</body></html>
"""


@pytest.fixture(autouse=True)
def public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every domain name resolves to a public IP, so tests never touch the network."""
    monkeypatch.setattr(offer_fetcher, "_resolve_ips", lambda hostname, port: [PUBLIC_IP])


@pytest.fixture
def no_page_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend trafilatura finds nothing, to test the JSON-LD path on its own."""
    monkeypatch.setattr(offer_fetcher.trafilatura, "extract", lambda *args, **kwargs: None)


def _html_response(body: str = OFFER_HTML, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code, headers={"content-type": "text/html; charset=utf-8"}, content=body.encode()
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/offre",
        "http://10.0.0.5/offre",
        "http://192.168.1.10/offre",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/offre",
        "http://[::ffff:127.0.0.1]/offre",
        "http://example.com:8080/offre",
        "file:///etc/passwd",
        "ftp://example.com/offre",
    ],
)
def test_forbidden_urls_are_blocked(url: str) -> None:
    with pytest.raises(offer_fetcher.UnsafeUrlError):
        offer_fetcher.fetch_offer_text(url)


def test_domain_resolving_to_private_ip_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(offer_fetcher, "_resolve_ips", lambda hostname, port: ["10.0.0.5"])

    with pytest.raises(offer_fetcher.UnsafeUrlError):
        offer_fetcher.fetch_offer_text(OFFER_URL)


def test_redirect_to_private_ip_is_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})

    with pytest.raises(offer_fetcher.UnsafeUrlError):
        offer_fetcher.fetch_offer_text(OFFER_URL, transport=httpx.MockTransport(handler))


def test_extracts_main_text_from_html() -> None:
    transport = httpx.MockTransport(lambda request: _html_response())

    text = offer_fetcher.fetch_offer_text(OFFER_URL, transport=transport)

    assert "Développeur Python backend" in text
    assert "FastAPI" in text


def test_follows_a_safe_redirect() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ancien-lien":
            return httpx.Response(301, headers={"location": "/offres/42"})
        return _html_response()

    text = offer_fetcher.fetch_offer_text(
        "https://jobs.example.com/ancien-lien", transport=httpx.MockTransport(handler)
    )

    assert "FastAPI" in text


def test_http_error_status_is_reported() -> None:
    transport = httpx.MockTransport(lambda request: _html_response("not found", 404))

    with pytest.raises(offer_fetcher.FetchFailedError):
        offer_fetcher.fetch_offer_text(OFFER_URL, transport=transport)


def test_too_many_redirects_is_reported() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"location": "/boucle"})
    )

    with pytest.raises(offer_fetcher.FetchFailedError):
        offer_fetcher.fetch_offer_text(OFFER_URL, transport=transport)


def test_page_without_text_is_reported() -> None:
    transport = httpx.MockTransport(
        lambda request: _html_response("<html><body><div></div></body></html>")
    )

    with pytest.raises(offer_fetcher.NoContentError):
        offer_fetcher.fetch_offer_text(OFFER_URL, transport=transport)


def test_non_html_content_is_rejected() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.7"
        )
    )

    with pytest.raises(offer_fetcher.NoContentError):
        offer_fetcher.fetch_offer_text(OFFER_URL, transport=transport)


JOB_POSTING = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": "Stage Data Analyst &amp; BI",
    "validThrough": "2026-12-19T00:00:00",
    "employmentType": "INTERN",
    "keywords": ["Python", "SQL", "Pandas"],
    "hiringOrganization": {"@type": "Organization", "name": "Thales"},
    "jobLocation": {
        "@type": "Place",
        "address": {"addressLocality": "Lyon", "addressCountry": "FR"},
    },
    "description": (
        "&lt;p&gt;Vous rejoignez l'équipe data pour construire des tableaux de bord.&lt;/p&gt;"
        "&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;li&gt;SQL&lt;/li&gt;&lt;/ul&gt;"
    ),
}

SIMILAR_JOBS_HTML = """
<h2>Offres d'emploi similaires</h2>
<ul><li>Ingénieur IA chez Esker</li><li>Tech lead IA chez SNCF</li></ul>
"""

SOFT_404_HTML = """
<html><body><article>
<p>Nous sommes désolés, l'emploi que vous recherchez n'existe plus ou a été retiré de notre
site. Consultez nos autres offres pour poursuivre votre recherche d'emploi chez nous.</p>
</article></body></html>
"""


def _page_with_json_ld(data: dict, body: str = "") -> str:
    return (
        '<html><head><script type="application/ld+json">'
        f"{json.dumps(data)}</script></head><body>{body}</body></html>"
    )


@pytest.mark.usefixtures("no_page_text")
def test_json_ld_job_posting_gives_a_clean_offer() -> None:
    page = _page_with_json_ld(JOB_POSTING, SIMILAR_JOBS_HTML)
    transport = httpx.MockTransport(lambda request: _html_response(page))

    text = offer_fetcher.fetch_offer_text(OFFER_URL, transport=transport)

    assert "Stage Data Analyst & BI" in text
    assert "Thales · Lyon, FR" in text
    assert "- Python" in text
    assert "<p>" not in text
    assert "Esker" not in text
    assert "similaires" not in text
    assert "Date d'expiration : 2026-12-19" in text
    assert "Type de contrat : INTERN" in text
    assert "Mots clés : Python, SQL, Pandas" in text


@pytest.mark.usefixtures("no_page_text")
def test_json_ld_job_posting_inside_graph_with_html_description() -> None:
    graph = {
        "@graph": [
            {"@type": "WebSite", "name": "Site carrières"},
            {
                "@type": "JobPosting",
                "title": "Data Analyst",
                "description": (
                    "<p>Analyse de données RH et reporting mensuel pour la direction.</p>"
                    "<p>Maîtrise de SQL exigée.</p>"
                ),
            },
        ]
    }
    page = _page_with_json_ld(graph)
    transport = httpx.MockTransport(lambda request: _html_response(page))

    text = offer_fetcher.fetch_offer_text(OFFER_URL, transport=transport)

    assert text.startswith("Data Analyst")
    assert "Maîtrise de SQL exigée." in text
    assert "<p>" not in text


def test_soft_404_page_is_rejected() -> None:
    transport = httpx.MockTransport(lambda request: _html_response(SOFT_404_HTML))

    with pytest.raises(offer_fetcher.NoContentError):
        offer_fetcher.fetch_offer_text(OFFER_URL, transport=transport)


def test_trim_boilerplate_cuts_the_similar_jobs_section() -> None:
    offer = "Stage Data Analyst. " * 20
    text = offer + "\nOffres d’emploi similaires\n- Ingénieur IA Esker"

    trimmed = offer_fetcher._trim_boilerplate(text)

    assert trimmed.startswith("Stage Data Analyst.")
    assert "Esker" not in trimmed


def test_clean_collapses_blank_lines_and_spaces() -> None:
    assert offer_fetcher._clean("  A  \n\n\n\n   \n B ") == "A\n\nB"


DESCRIPTION = "Analyse de données et développement de modèles prédictifs pour nos clients."
VISIBLE_TEXT = "\n".join(
    [
        "Stage PFE Data Scientist",
        "Postuler maintenant",
        DESCRIPTION,
        "Date d'expiration",
        "19/12/2026",
        "Mots clés: Python SQL Pandas",
        "Mots clés: Python SQL Pandas",
    ]
)


def test_extra_facts_keeps_only_what_the_json_ld_misses() -> None:
    structured = f"Stage PFE Data Scientist\n\n{DESCRIPTION}"

    extras = offer_fetcher._extra_facts(VISIBLE_TEXT, structured)

    assert extras == "Date d'expiration\n19/12/2026\nMots clés: Python SQL Pandas"


def test_json_ld_offer_is_completed_with_facts_from_the_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(offer_fetcher.trafilatura, "extract", lambda *args, **kwargs: VISIBLE_TEXT)
    posting = {
        "@type": "JobPosting",
        "title": "Stage PFE Data Scientist",
        "description": DESCRIPTION,
    }
    page = _page_with_json_ld(posting)
    transport = httpx.MockTransport(lambda request: _html_response(page))

    text = offer_fetcher.fetch_offer_text(OFFER_URL, transport=transport)

    assert "Date d'expiration" in text
    assert "19/12/2026" in text
    assert "Mots clés: Python SQL Pandas" in text
    assert text.count("Analyse de données") == 1
    assert "Postuler" not in text


def test_json_ld_with_a_raw_newline_inside_a_string_is_still_read() -> None:
    page = """<script type="application/ld+json">
{"@type": "JobPosting", "title": "Data Analyst",
 "description": "Première ligne de l'offre
Deuxième ligne de l'offre, assez longue pour dépasser cinquante caractères."}
</script>"""

    text = offer_fetcher._text_from_json_ld(page)

    assert text is not None
    assert "Deuxième ligne" in text


def test_extra_facts_merges_labels_with_values_and_skips_page_chrome() -> None:
    visible = "\n".join(
        [
            "Emploi Tunisie » Offres d'emploi à Tunis » Stage PFE",
            "- Il'y a 11 heures",
            "- Experience :",
            "- Débutant",
        ]
    )

    extras = offer_fetcher._extra_facts(visible, "Stage PFE\n\nDescription")

    assert extras == "- Experience : Débutant"


def test_html_is_cut_at_the_similar_jobs_heading(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_extract(page: str, **kwargs) -> str:
        seen.append(page)
        return "Texte de l'offre " * 10

    monkeypatch.setattr(offer_fetcher.trafilatura, "extract", fake_extract)
    page = (
        "<body><h1>Offre</h1><p>Texte</p>"
        "<h2>Offres d&#039;emploi similaires sponsorisées</h2><p>Esker</p></body>"
    )

    offer_fetcher._visible_text(page)

    assert "Texte" in seen[0]
    assert "Esker" not in seen[0]


def test_visible_text_retries_on_the_full_page_if_the_cut_removes_the_offer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_extract(page: str, **kwargs) -> str:
        return "Contenu de l'offre complet " * 5 if "Contenu" in page else ""

    monkeypatch.setattr(offer_fetcher.trafilatura, "extract", fake_extract)

    text = offer_fetcher._visible_text("<h2>Similar jobs</h2><p>Contenu</p>")

    assert text.startswith("Contenu")


META_KEYWORDS = (
    "offre d'emploi Stage PFE, offres d'emploi Bestlab, recrutement chez Bestlab, "
    "Bestlab, Python, SQL, Python<!--, Bestlab, Python, -->"
)


def test_meta_keywords_drop_seo_phrases_and_duplicates() -> None:
    page = f'<meta name="keywords" content="{META_KEYWORDS}"><b>Mots clés:</b>'

    assert offer_fetcher._meta_keywords(page) == "Bestlab, Python, SQL"


def test_meta_keywords_are_ignored_when_the_page_shows_no_keywords_section() -> None:
    page = '<meta name="keywords" content="Python, SQL"><p>Une offre.</p>'

    assert offer_fetcher._meta_keywords(page) == ""


@pytest.mark.usefixtures("no_page_text")
def test_offer_gets_a_keywords_line_from_the_meta_tag() -> None:
    posting = {
        "@type": "JobPosting",
        "title": "Stage PFE Data Scientist",
        "description": DESCRIPTION,
    }
    meta_tag = '<meta name="keywords" content="Bestlab, Python, SQL">'
    page = meta_tag + _page_with_json_ld(posting, "<b>Mots clés:</b>")
    transport = httpx.MockTransport(lambda request: _html_response(page))

    text = offer_fetcher.fetch_offer_text(OFFER_URL, transport=transport)

    assert text.endswith("Mots clés : Bestlab, Python, SQL")
