"""Python ghost state: instantiate once per state-machine example."""
from dataclasses import dataclass, field


@dataclass
class Model:
    balances: dict = field(default_factory=dict)
    entities: list = field(default_factory=list)
