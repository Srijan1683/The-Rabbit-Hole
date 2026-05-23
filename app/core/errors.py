class RabbitHoleError(Exception):
    pass


class NotFoundError(RabbitHoleError):
    pass


class ExternalAPIError(RabbitHoleError):
    pass


class RateLimitError(ExternalAPIError):
    pass


class ConfigurationError(RabbitHoleError):
    pass