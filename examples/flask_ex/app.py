from flask import Flask, render_template, request
from micawber.providers import bootstrap_basic
from micawber.contrib.mcflask import add_oembed_filters

app = Flask(__name__)
app.config['DEBUG'] = True

oembed_providers = bootstrap_basic()
add_oembed_filters(app, oembed_providers)

@app.route('/')
def example_view():
    text = request.args.get('text', 'https://www.youtube.com/watch?v=nda_OSWeyn8')
    html = request.args.get('html', """
<p>This is a test</p>
<p>https://www.youtube.com/watch?v=nda_OSWeyn8</p>
<p>This will get rendered as a link: https://www.youtube.com/watch?v=nda_OSWeyn8</p>
<p>This will not be modified: <a href="https://www.google.com/">https://www.youtube.com/watch?v=nda_OSWeyn8</a></p>
    """)
    return render_template('example.html', text=text, html=html)

if __name__ == '__main__':
    app.run()
