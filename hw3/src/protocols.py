from __future__ import annotations

import functools
import itertools
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable, TypeVar

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


@dataclass
class Host:
    packets: list[int]
    """Timepoints when the host generates a packet."""

    sending_progress: int = 0
    """The progress of sending a packet."""

    def is_sending(self) -> bool:
        return self.sending_progress > 0

    def has_packet(self, time: int) -> bool:
        return len(self.packets) > 0 and self.packets[0] <= time

    def get_action(self, time: int, can_start: bool = True) -> TransmissionStatus:
        if self.is_sending():
            return TransmissionStatus.Sending

        if self.has_packet(time) and can_start:
            return TransmissionStatus.Start

        return TransmissionStatus.Idle


def extract_success_packets(history: list[TransmissionStatus]):
    return SUCCESS_PATTERN.findall("".join(map(str, history)))


def calculate_statistics(setting: Setting, history: list[list[TransmissionStatus]]):
    """Calculate the statistics of the simulation."""

    success_packets = itertools.chain(*(extract_success_packets(h) for h in history))
    success_count = sum(len(success_packet) for success_packet in success_packets)

    idle_count = sum(
        all(h[i] == TransmissionStatus.Idle for h in history)
        for i in range(setting.total_time)
    )

    success_rate = success_count / setting.total_time
    idle_rate = idle_count / setting.total_time
    return (success_rate, idle_rate, 1 - success_rate - idle_rate)


T = TypeVar("T")


def transposed(m: list[list[T]]) -> list[list[T]]:
    return [list(row) for row in zip(*m)]


def mac_protocol(
    impl: Callable[
        [list[Host], list[list[TransmissionStatus]], Setting, int],
        list[TransmissionStatus],
    ]
) -> Callable[[Setting, bool], tuple[float, float, float]]:
    """Decorator for creating MAC protocols."""

    @functools.wraps(impl)
    def wrapper(
        setting: Setting, show_history: bool = False
    ) -> tuple[float, float, float]:
        packets = setting.gen_packets()
        hosts = [Host(p.copy()) for p in packets]
        history: list[list[TransmissionStatus]] = []

        for time in range(setting.total_time):
            actions = impl(hosts, history, setting, time)

            # update the history
            history.append(actions)

        history = transposed(history)

        if show_history:
            print(impl.__name__)

            for i, h in enumerate(history):
                # print a 'V' on the timepoint when the host generates a packet
                spaces = " " * len(f"h{i}: ")
                generated_timestamps = "".join(
                    "V" if time in packets[i] else " "
                    for time in range(setting.total_time)
                )
                print(f"{spaces}{generated_timestamps}")

                # print the history of the host
                print(f"h{i}:", "".join(map(str, h)))

            print()

        return calculate_statistics(setting, history)

    return wrapper


@mac_protocol
def aloha(
    hosts: list[Host],
    history: list[list[TransmissionStatus]],
    setting: Setting,
    time: int,
) -> list[TransmissionStatus]:
    # decide the action of each host
    actions = [host.get_action(time) for host in hosts]

    # update the sending progress of each host
    for host, action in zip(hosts, actions):
        if action == TransmissionStatus.Sending:
            host.sending_progress += 1
        if action == TransmissionStatus.Start:
            host.sending_progress = 1

    # stop sending if the packet is finished
    for i, host in enumerate(hosts):
        if host.sending_progress != setting.packet_time:
            continue

        host.sending_progress = 0
        has_collision = any(
            any(
                status != TransmissionStatus.Idle
                for status in itertools.chain(h[:i], h[i + 1 :])
            )
            for h in itertools.chain(
                history[time - setting.packet_time + 1 : time], [actions]
            )
        )

        if has_collision:
            actions[i] = TransmissionStatus.Collision
            host.packets[0] = time + random.randint(1, setting.max_colision_wait_time)
            continue

        host.packets.pop(0)
        actions[i] = TransmissionStatus.Success

    return actions


@mac_protocol
def slotted_aloha(
    hosts: list[Host],
    history: list[list[TransmissionStatus]],
    setting: Setting,
    time: int,
) -> list[TransmissionStatus]:
    # decide the action of each host
    actions = [
        host.get_action(time, can_start=time % setting.packet_time == 0)
        for host in hosts
    ]

    # update the sending progress of each host
    for host, action in zip(hosts, actions):
        if action == TransmissionStatus.Sending:
            host.sending_progress += 1
        if action == TransmissionStatus.Start:
            host.sending_progress = 1

    # stop sending if the packet is finished
    for i, host in enumerate(hosts):
        if host.sending_progress != setting.packet_time:
            continue

        host.sending_progress = 0
        has_collision = any(
            any(
                status != TransmissionStatus.Idle
                for status in itertools.chain(h[:i], h[i + 1 :])
            )
            for h in itertools.chain(
                history[time - setting.packet_time + 1 : time], [actions]
            )
        )

        if has_collision:
            actions[i] = TransmissionStatus.Collision

            # calculate the time to resend the packet
            wait_slot_num = sum(
                itertools.takewhile(
                    lambda _: random.random() > setting.p_resend, itertools.repeat(1)
                )
            )

            host.packets[0] = time + 1 + (wait_slot_num * setting.packet_time)
            continue

        host.packets.pop(0)
        actions[i] = TransmissionStatus.Success

    return actions


@mac_protocol
def csma(
    hosts: list[Host],
    history: list[list[TransmissionStatus]],
    setting: Setting,
    time: int,
) -> list[TransmissionStatus]:
    raise NotImplementedError()


@mac_protocol
def csma_cd(
    hosts: list[Host],
    history: list[list[TransmissionStatus]],
    setting: Setting,
    time: int,
) -> list[TransmissionStatus]:
    raise NotImplementedError()
