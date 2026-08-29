class ProviderError(Exception):
    pass

class ProviderStatusError(Exception):
    pass

class ProviderTimeoutError(ProviderError):
    pass