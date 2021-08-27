import enum


class UiState(enum.Enum):
    stopped = 1
    running = 2
    paused = 3
    reached_limit = 4  # when daily limited reached
