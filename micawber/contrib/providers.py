import re

from micawber.providers import Provider


class ImageProvider(Provider):
    """
    Simple little hack to render any image URL as an <img> tag, use with care

    Usage:

    pr = micawber.bootstrap_basic()
    pr.register(ImageProvider.regex, ImageProvider(''))
    """
    regex = 'http://.+?\.(jpg|gif|png)'

    def request(self, url, **params):
        return {
            'url': url,
            'type': 'photo',
            'title': '',
        }


class GoogleMapsProvider(Provider):
    """
    Render a map URL as an embedded map

    Usage:

    pr = micawber.bootstrap_basic()
    pr.register(GoogleMapsProvider.regex, GoogleMapsProvider(''))
    """
    regex = r'^https?://maps.google.com/maps\?([^\s]+)'
    
    valid_params = ['q', 'z']
    
    def request(self, url, **params):
        url_params = re.match(self.regex, url).groups()[0]
        url_params = url_params.replace('&amp;', '&').split('&')
        
        map_params = ['output=embed']
        
        for param in url_params:
            k, v = param.split('=', 1)
            if k in self.valid_params:
                map_params.append(param)
        
        width = int(params.get('maxwidth', 640))
        height = int(params.get('maxheight', 480))
        html = '<iframe width="%d" height="%d" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" src="http://maps.google.com/maps?%s"></iframe>' % \
            (width, height, '&amp;'.join(map_params))
        
        return {
            'height': height,
            'html': html,
            'provider_name': 'Google maps',
            'title': '',
            'type': 'rich',
            'version': '1.0',
            'width': width,
        }
