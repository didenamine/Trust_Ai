"""Title and description of an offer, derived from its text (used by the "my offers" list)."""

TITLE_MAX_CHARS = 120
_MARKUP_CHARS = " \t#*-•>"  # markdown headings, bullets and quotes before a title


def split_title_and_description(content: str) -> tuple[str, str]:
    """The title is the first non-empty line; the description is everything after it.

    A first line too long to be a title (a pasted paragraph) is shortened to make the title,
    and the description is then the whole text.
    """
    text = content.strip()
    first_line, _, rest = text.partition("\n")
    title = first_line.strip().lstrip(_MARKUP_CHARS).strip() or first_line.strip()
    if len(title) > TITLE_MAX_CHARS:
        shortened = title[:TITLE_MAX_CHARS].rsplit(" ", 1)[0]
        return f"{shortened}…", text
    return title, rest.strip()
