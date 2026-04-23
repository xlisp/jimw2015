import markdown as md
from markupsafe import Markup


def markdown_filter(text: str | None) -> Markup:
    if not text:
        return Markup("")
    html = md.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br", "codehilite"],
        output_format="html5",
    )
    return Markup(html)
