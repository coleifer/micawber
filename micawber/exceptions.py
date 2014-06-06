class ProviderException(Exception):
    pass

class ProviderNotFoundException(ProviderException):
    pass

class ProviderBadResponseException(ProviderException):
    pass
