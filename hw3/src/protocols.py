import functools
import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol, Sequence

from setting import Setting


class TransmissionStatus(Enum):
    Start = "<"
    Sending = "-"
    Success = ">"
    Idle = "."
    Collision = "|"

    def __str__(self) -> str:
        return self.value


SUCCESS_PATTERN = re.compile(r"<-*>")
COLLISION_PATTERN = re.compile(r"<-*\|")


def print_history(
    packets: list[list[int]], history: list[list[TransmissionStatus]]
) -> None:
    """Print the history of the simulation."""

    for packet_times, host in zip(packets, history):
        # TODO: print the packet times in the specified format
        print(packet_times)
        print("".join(map(str, host)))


def create_summary(
    total_time: int, history: list[list[TransmissionStatus]]
) -> tuple[float, float, float]:
    """Create a summary of the simulation."""

    def count_status(host: list[TransmissionStatus], pattern: re.Pattern[str]) -> int:
        string_history = "".join(map(str, host))
        matched = pattern.findall(string_history)
        return sum(len(m) for m in matched)

    success_count = sum(count_status(host, SUCCESS_PATTERN) for host in history)
    collision_count = sum(count_status(host, COLLISION_PATTERN) for host in history)
    idle_count = sum(host.count(TransmissionStatus.Idle) for host in history)

    success_rate = success_count / total_time
    collision_rate = collision_count / total_time
    idle_rate = idle_count / total_time

    return success_rate, collision_rate, idle_rate


class MacProtocol(Protocol):
    """Represents a MAC protocol."""

    def __init__(self, setting: Setting) -> None:
        """Instantiate a MAC protocol object."""
        raise NotImplementedError()

    def run_simulation(
        self, packets: Sequence[Sequence[int]]
    ) -> list[list[TransmissionStatus]]:
        """Run the simulation."""
        raise NotImplementedError()

    @property
    def name(self) -> str:
        """The name of the protocol."""
        raise NotImplementedError()


def mac_protocol(
    strategy: Callable[[Setting], MacProtocol],
) -> Callable[[Setting, bool], tuple[float, float, float]]:
    """Decorator for MAC protocol implementations."""

    @functools.wraps(strategy)
    def wrapper(
        setting: Setting, show_history: bool = False
    ) -> tuple[float, float, float]:
        impl = strategy(setting)
        packets = setting.gen_packets()
        simulation_result = impl.run_simulation(packets)

        if show_history:
            print(impl.name)
            print_history(packets, simulation_result)

        return create_summary(setting.total_time, simulation_result)

    return wrapper


@dataclass
class AlohaImpl:
    setting: Setting
    name = "aloha"

    def run_simulation(
        self, packets: Sequence[Sequence[int]]
    ) -> list[list[TransmissionStatus]]:
        raise NotImplementedError()


@mac_protocol
def aloha(setting: Setting):
    return AlohaImpl(setting)


@dataclass
class SlottedAlohaImpl:
    setting: Setting
    name = "slotted_aloha"

    def run_simulation(
        self, packets: Sequence[Sequence[int]]
    ) -> list[list[TransmissionStatus]]:
        raise NotImplementedError()


@mac_protocol
def slotted_aloha(setting: Setting):
    return SlottedAlohaImpl(setting)


@dataclass
class CsmaImpl:
    setting: Setting
    name = "csma"

    def run_simulation(
        self, packets: Sequence[Sequence[int]]
    ) -> list[list[TransmissionStatus]]:
        raise NotImplementedError()


@mac_protocol
def csma(setting: Setting):
    return CsmaImpl(setting)


@dataclass
class CsmaCdImpl:
    setting: Setting
    name = "csma_cd"

    def run_simulation(
        self, packets: Sequence[Sequence[int]]
    ) -> list[list[TransmissionStatus]]:
        raise NotImplementedError()


@mac_protocol
def csma_cd(setting: Setting):
    return CsmaCdImpl(setting)
