class MetadataError(Exception):
    pass


class MetadataStatusError(Exception):
    pass


class MetadataTimeoutError(MetadataError):
    pass
