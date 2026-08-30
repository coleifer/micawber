from django.shortcuts import render_to_response

def example_view(request):
    text = request.GET.get('text', 'https://www.youtube.com/watch?v=nda_OSWeyn8')
    html = request.GET.get('html', """
<p>This is a test</p>
<p>https://www.youtube.com/watch?v=nda_OSWeyn8</p>
<p>This will get rendered as a link: https://www.youtube.com/watch?v=nda_OSWeyn8</p>
<p>This will not be modified: <a href="https://www.google.com/">https://www.youtube.com/watch?v=nda_OSWeyn8</a></p>
    """)
    return render_to_response('example.html', dict(
        text=text,
        html=html,
    ))
