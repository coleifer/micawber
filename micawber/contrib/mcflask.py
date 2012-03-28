from flask import Markup
from micawber import parse_text, parse_html, extract, extract_html


def oembed(s, providers, urlize_all=True, html=False):
    if html:
        fn = parse_html
    else:
        fn = parse_text
    return Markup(fn(s, providers, urlize_all))

def add_oembed_filters(app, providers):
    def _oembed(s, urlize_all=True, html=False):
        return oembed(s, providers, urlize_all, html)
    app.jinja_env.filters['oembed'] = _oembed
