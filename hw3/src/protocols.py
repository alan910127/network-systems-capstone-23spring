from __future__ import annotations

import functools
import itertools
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, Sequence, TypeVar

from setting import Setting


class TransmissionStatus(Enum):
    Start = "<"
    Sending = "-"
    Success = ">"
    Idle = "."
    Collision = "|"

    def __str__(self) -> str:
        return self.value

    def is_idle_lossy(self):
        return self in (self.Idle, self.Success, self.Collision)


SUCCESS_PATTERN = re.compile(r"<-*>")


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

    def get_action(self, time: int) -> TransmissionStatus:
        if self.is_sending():
            return TransmissionStatus.Sending

        if self.has_packet(time):
            return TransmissionStatus.Start

        return TransmissionStatus.Idle

    def wait_until(self, time: int):
        self.packets[0] = time

    def finish_packet(self):
        self.sending_progress = 0
        self.packets.pop(0)


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


def transposed(m: Iterable[Iterable[T]]) -> list[list[T]]:
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


def update_progress(
    hosts: Iterable[Host], actions: Iterable[TransmissionStatus]
) -> None:
    for host, action in zip(hosts, actions):
        if action == TransmissionStatus.Sending:
            host.sending_progress += 1
        if action == TransmissionStatus.Start:
            host.sending_progress = 1


def finished_hosts(hosts: Iterable[Host], packet_time: int):
    yield from (
        (i, host)
        for i, host in enumerate(hosts)
        if host.sending_progress == packet_time
    )


def non_self_statuses(history: Iterable[Sequence[TransmissionStatus]], host_id: int):
    for h in history:
        yield from itertools.chain(h[:host_id], h[host_id + 1 :])


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
    update_progress(hosts, actions)

    # stop sending if the packet is finished
    for i, host in finished_hosts(hosts, setting.packet_time):
        host.sending_progress = 0
        has_collision = any(
            status != TransmissionStatus.Idle
            for status in non_self_statuses(
                itertools.chain(history[-setting.packet_time + 1 :], [actions]), i
            )
        )

        if has_collision:
            actions[i] = TransmissionStatus.Collision
            host.wait_until(time + random.randint(1, setting.max_colision_wait_time))
            continue

        host.finish_packet()
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
    actions = [host.get_action(time) for host in hosts]

    # one can only start sending if it's at the beginning of the time slot
    can_start = time % setting.packet_time == 0
    for i, action in enumerate(actions):
        if action == TransmissionStatus.Start and not can_start:
            actions[i] = TransmissionStatus.Idle

    # update the sending progress of each host
    update_progress(hosts, actions)

    # stop sending if the packet is finished
    for i, host in finished_hosts(hosts, setting.packet_time):
        host.sending_progress = 0
        has_collision = any(
            status != TransmissionStatus.Idle
            for status in non_self_statuses(
                itertools.chain(history[-setting.packet_time + 1 :], [actions]), i
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

            host.wait_until(time + 1 + (wait_slot_num * setting.packet_time))
            continue

        host.finish_packet()
        actions[i] = TransmissionStatus.Success

    return actions


@mac_protocol
def csma(
    hosts: list[Host],
    history: list[list[TransmissionStatus]],
    setting: Setting,
    time: int,
) -> list[TransmissionStatus]:
    def can_start(host_id: int):
        result = time <= setting.link_delay or all(
            status.is_idle_lossy()
            for status in non_self_statuses([history[-setting.link_delay - 1]], host_id)
        )
        return result

    # decide the action of each host
    actions = [host.get_action(time) for host in hosts]

    # one can only start sending if there's no packet being sent in the link
    for i, (host, action) in enumerate(zip(hosts, actions)):
        if action == TransmissionStatus.Start and not can_start(i):
            actions[i] = TransmissionStatus.Idle

            # wait for a random time before trying again
            host.wait_until(time + random.randint(1, setting.max_colision_wait_time))

    # update the sending progress of each host
    update_progress(hosts, actions)

    # stop sending if the packet is finished
    for i, host in finished_hosts(hosts, setting.packet_time):
        host.sending_progress = 0

        has_collision = any(
            status != TransmissionStatus.Idle
            for status in non_self_statuses(
                itertools.chain(history[-setting.packet_time + 1 :], [actions]), i
            )
        )

        if has_collision:
            actions[i] = TransmissionStatus.Collision
            host.wait_until(time + random.randint(1, setting.max_colision_wait_time))
            continue

        host.finish_packet()
        actions[i] = TransmissionStatus.Success

    return actions


@mac_protocol
def csma_cd(
    hosts: list[Host],
    history: list[list[TransmissionStatus]],
    setting: Setting,
    time: int,
) -> list[TransmissionStatus]:
    def can_start(host_id: int):
        result = time <= setting.link_delay or all(
            status.is_idle_lossy()
            for status in non_self_statuses([history[-setting.link_delay - 1]], host_id)
        )
        return result

    # decide the action of each host
    actions = [host.get_action(time) for host in hosts]

    # one can only start sending if there's no packet being sent in the link
    for i, (host, action) in enumerate(zip(hosts, actions)):
        if action == TransmissionStatus.Start and not can_start(i):
            actions[i] = TransmissionStatus.Idle

            # wait for a random time before trying again
            host.wait_until(time + random.randint(1, setting.max_colision_wait_time))

    # update the sending progress of each host
    update_progress(hosts, actions)

    # detect collision, or stop sending if the packet is finished
    for i, host in enumerate(hosts):
        if actions[i] == TransmissionStatus.Idle:
            continue

        window_start = max(time - host.sending_progress - setting.link_delay + 1, 0)
        window_end = max(time - setting.link_delay, 0)
        has_collision = time >= setting.link_delay and any(
            status != TransmissionStatus.Idle
            for status in non_self_statuses(
                itertools.chain(
                    history[window_start:window_end],
                    (actions,) if setting.link_delay == 0 else (),
                ),
                i,
            )
        )

        if has_collision:
            host.sending_progress = 0
            host.wait_until(time + random.randint(1, setting.max_colision_wait_time))
            actions[i] = TransmissionStatus.Collision
            continue

        if host.sending_progress != setting.packet_time:
            # keep sending
            continue

        host.finish_packet()
        actions[i] = TransmissionStatus.Success

    return actions
