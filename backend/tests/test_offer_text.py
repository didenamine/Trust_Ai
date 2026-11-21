from app.services.offer_text import TITLE_MAX_CHARS, split_title_and_description


def test_title_is_the_first_line_and_description_the_rest() -> None:
    title, description = split_title_and_description(
        "Stage PFE Data Scientist\nBestlab · Tunis\n\nAnalyse de données."
    )

    assert title == "Stage PFE Data Scientist"
    assert description == "Bestlab · Tunis\n\nAnalyse de données."


def test_leading_blank_lines_and_markdown_marks_are_ignored() -> None:
    title, description = split_title_and_description(
        "\n\n## Stage PFE Data Scientist\nTexte de l'offre"
    )

    assert title == "Stage PFE Data Scientist"
    assert description == "Texte de l'offre"


def test_a_single_short_line_has_no_description() -> None:
    assert split_title_and_description("Stage PFE Data Scientist") == (
        "Stage PFE Data Scientist",
        "",
    )


def test_a_long_first_line_is_shortened_and_the_description_keeps_the_whole_text() -> None:
    text = "Vous concevez des API REST avec FastAPI. " * 10

    title, description = split_title_and_description(text)

    assert title.endswith("…")
    assert len(title) <= TITLE_MAX_CHARS + 1
    assert description == text.strip()


def test_empty_content_gives_an_empty_title_and_description() -> None:
    assert split_title_and_description("") == ("", "")
