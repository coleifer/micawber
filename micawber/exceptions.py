class ProviderException(Exception):
    pass

class ProviderNotFoundException(ProviderException):
    pass

class InvalidResponseException(ProviderException):
    pass
