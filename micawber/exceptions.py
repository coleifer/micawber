class ProviderException(Exception):
    pass

class ProviderNotFoundException(ProviderException):
    pass

class InvalidResponseException(ProviderException):
    pass

class ProviderTimeoutException(ProviderException):
    pass

class ProviderHTTPException(ProviderException):
    def __init__(self, url, status):
        super().__init__('HTTP %s fetching "%s"' % (status, url))
        self.url = url
        self.status = status
