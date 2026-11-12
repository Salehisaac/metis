# Translate this Go function to Python, using an exception instead of an error value.
#
#   var ErrPort = errors.New("port")
#
#   func ParsePort(s string) (int, error) {
#       n, err := strconv.Atoi(strings.TrimSpace(s))
#       if err != nil {
#           return 0, fmt.Errorf("invalid port %q: %w", s, err)
#       }
#       if n < 1 || n > 65535 {
#           return 0, fmt.Errorf("port %d out of range 1-65535: %w", n, ErrPort)
#       }
#       return n, nil
#   }
#
# 1. Define PortError, a subclass of ValueError.
# 2. Implement parse_port. The exact messages are in exercise.json.


def parse_port(text: str) -> int:
    raise NotImplementedError
