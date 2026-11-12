class PortError(ValueError):
    pass


def parse_port(text: str) -> int:
    try:
        port = int(text)
    except ValueError as err:
        raise PortError(f"invalid port {text!r}") from err
    if not 1 <= port <= 65535:
        raise PortError(f"port {port} out of range 1-65535")
    return port
