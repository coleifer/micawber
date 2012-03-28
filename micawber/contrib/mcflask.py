from flask import Markup
from micawber import parse_text, parse_html, extract, extract_html


def oembed(s, providers, urlize_all=True, html=False, **params):
    if html:
        fn = parse_html
    else:
        fn = parse_text
    return Markup(fn(s, providers, urlize_all, **params))

def extract_oembed(s, providers, html=False, **params):
    if html:
        fn = extract_html
    else:
        fn = extract
    return fn(s, providers, **params)

def add_oembed_filters(app, providers):
    def _oembed(s, urlize_all=True, html=False, **params):
        return oembed(s, providers, urlize_all, html, **params)

    def _extract_oembed(s, html=False, **params):
        return extract_oembed(s, providers, html, **params)

    app.jinja_env.filters['oembed'] = _oembed
    app.jinja_env.filters['extract_oembed'] = _extract_oembed
