__all__ = ["Power", "Mode", "Output", "SCU", "NoSCU"]

import enum


class Power(str, enum.Enum):
    ON = "ON"
    OFF = "OFF"
    FAULT = "FAULT"


class Mode(str, enum.Enum):
    CONTINUOUS = "Continuous"
    BURST = "Burst"
    TRIGGER = "Trigger"


class Output(str, enum.Enum):
    OFF = "OFF"
    ADJUST = "Adjust"
    MAX = "MAX"


class SCU(str, enum.Enum):
    SCU = "SCU"
    F1_SCU = "F1 SCU"
    F2_SCU = "F2 SCU"


class NoSCU(str, enum.Enum):
    NO_SCU = "No SCU"
    F1_NO_SCU = "F1 No SCU"
    F2_NO_SCU = "F2 No SCU"
