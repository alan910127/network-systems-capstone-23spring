#!/usr/bin/env python3

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from heapq import heappop, heappush
from typing import Generic, Protocol, TypeVar

NO_LINK = 999
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nscap")


class Message(Protocol):
    source: int
    destination: int


T = TypeVar("T", bound=Message)


class MessageService(Generic[T]):
    def __init__(self):
        self.messages: list[T] = []

    def send(self, message: T):
        self.messages.append(message)

    def get_messages(self, id: int) -> list[T]:
        return [m for m in self.messages if m.destination == id]

    def reset(self):
        self.messages = []


@dataclass
class LinkState:
    source: int
    destination: int
    originator: int
    link_cost: list[int]


class OspfRouter:
    def __init__(self, id: int, link_cost: list[int]):
        self.id = id
        link_cost = link_cost.copy()
        self.link_cost = [
            link_cost if i == id else [999] * len(link_cost)
            for i, _ in enumerate(link_cost)
        ]
        self.updated_link_states = [(id, link_cost)]

    def __repr__(self):
        return f"OspfRouter(id={self.id})"

    def send_link_state(self, router: OspfRouter, service: MessageService[LinkState]):
        """Send the link state to the router."""

        for id, link_cost in self.updated_link_states:
            logger.debug(f"Router {self.id} sends link state of {id} to {router.id}.")
            service.send(
                LinkState(
                    source=self.id,
                    destination=router.id,
                    originator=id,
                    link_cost=link_cost,
                )
            )

    def receive_link_state(self, service: MessageService[LinkState]):
        """Receive the link state sent by neighbors."""

        messages: list[LinkState] = []

        def find_duplicate(link_cost: list[int]):
            for i, message in enumerate(messages):
                if message.link_cost == link_cost:
                    return i
            return None

        for message in service.get_messages(self.id):
            id = message.originator
            link_cost = message.link_cost

            # ignore the link state if it is not updated.
            if self.link_cost[id] == link_cost:
                continue

            logger.debug(f"Router {self.id} receives link state of {id}.")

            if (idx := find_duplicate(link_cost)) is not None:
                if messages[idx].source > message.source:
                    messages[idx] = message

                continue

            messages.append(message)

        self.updated_link_states = [(m.originator, m.link_cost) for m in messages]
        return messages

    def update(self) -> bool:
        """Update the link cost matrix from a router's link."""

        updated = False

        for id, link_cost in self.updated_link_states:
            for i, cost in enumerate(link_cost):
                if cost < self.link_cost[id][i]:
                    self.link_cost[id][i] = cost
                    updated = True

        return updated

    def shortest_paths(self):
        """Get the shortest paths from the router to other routers."""

        heap = [(0, self.id)]
        shortest_path = [999] * len(self.link_cost)

        while heap:
            cost, id = heappop(heap)
            if cost >= shortest_path[id]:
                continue
            shortest_path[id] = cost
            for i, cost in enumerate(self.link_cost[id]):
                path_distance = cost + shortest_path[id]
                if path_distance < shortest_path[i]:
                    heappush(heap, (path_distance, i))

        return shortest_path


def run_ospf(
    link_cost: list[list[int]],
) -> tuple[list[list[int]], list[tuple[int, int, int]]]:
    routers = [OspfRouter(i, cost) for i, cost in enumerate(link_cost)]
    direct_links = [
        (r1, r2)
        for (i, r1), (j, r2) in itertools.permutations(enumerate(routers), 2)
        if link_cost[i][j] != NO_LINK
    ]
    message_service: MessageService[LinkState] = MessageService()

    # (source, link state owner, destination)
    records: list[list[tuple[int, int, int]]] = []

    is_converged = False

    while not is_converged:
        for r1, r2 in direct_links:
            r1.send_link_state(r2, message_service)

        records.append([])
        for router in routers:
            messages = router.receive_link_state(message_service)
            records[-1].extend(
                (m.source, m.originator, m.destination) for m in messages
            )

        updated = [router.update() for router in routers]

        # if any router is updated, the network is not converged.
        is_converged = not any(updated)

        message_service.reset()

    shortest_paths = [router.shortest_paths() for router in routers]
    logs = list(itertools.chain(*(sorted(record) for record in records)))

    return shortest_paths, logs


@dataclass
class DistanceVector:
    source: int
    destination: int
    distance_vector: list[int]


class RipRouter:
    def __init__(self, id: int, distance_vector: list[int]):
        self.id = id
        self.distance_vector = distance_vector.copy()
        self.messages: list[DistanceVector] = []
        self.is_converged = False

    def __repr__(self):
        return f"RipRouter(id={self.id})"

    def send_distance_vector(
        self, router: RipRouter, service: MessageService[DistanceVector]
    ):
        if self.is_converged:
            return

        logger.debug(f"Router {self.id} sends its distance vector to {router.id}.")
        service.send(
            DistanceVector(
                source=self.id,
                destination=router.id,
                distance_vector=self.distance_vector,
            )
        )

    def receive_distance_vector(self, service: MessageService[DistanceVector]):
        self.messages = service.get_messages(self.id)
        return self.messages

    def update(self) -> bool:
        new_distance_vector = self.distance_vector.copy()
        for message in self.messages:
            for i, cost in enumerate(message.distance_vector):
                new_cost = cost + self.distance_vector[message.source]
                if new_cost < self.distance_vector[i]:
                    new_distance_vector[i] = new_cost

        updated = new_distance_vector != self.distance_vector
        self.distance_vector = new_distance_vector
        self.is_converged = not updated
        return updated


def run_rip(
    link_cost: list[list[int]],
) -> tuple[list[list[int]], list[tuple[int, int]]]:
    routers = [RipRouter(i, cost) for i, cost in enumerate(link_cost)]
    direct_links = [
        (r1, r2)
        for (i, r1), (j, r2) in itertools.permutations(enumerate(routers), 2)
        if link_cost[i][j] != NO_LINK
    ]

    message_service: MessageService[DistanceVector] = MessageService()

    # (source, destination)
    records: list[list[tuple[int, int]]] = []

    is_converged = False

    while not is_converged:
        for r1, r2 in direct_links:
            r1.send_distance_vector(r2, message_service)

        records.append([])
        for router in routers:
            messages = router.receive_distance_vector(message_service)
            records[-1].extend((m.source, m.destination) for m in messages)

        updated = [router.update() for router in routers]

        # if any router is updated, the network is not converged.
        is_converged = not any(updated)

        message_service.reset()

    shortest_paths = [router.distance_vector for router in routers]
    logs = list(itertools.chain(*(sorted(record) for record in records)))

    return shortest_paths, logs


TEST_DATA = [
    [
        [0, 2, 5, 1, 999, 999],
        [2, 0, 3, 2, 999, 999],
        [5, 3, 0, 3, 1, 5],
        [1, 2, 3, 0, 1, 999],
        [999, 999, 1, 1, 0, 2],
        [999, 999, 5, 999, 2, 0],
    ],
    [
        [0, 4, 1, 999],
        [4, 0, 2, 999],
        [1, 2, 0, 3],
        [999, 999, 3, 0],
    ],
]


def main():
    test_ospf()
    test_rip()


def test_ospf():
    ospf_result = [run_ospf(link_cost) for link_cost in TEST_DATA]

    assert ospf_result[0] == (
        [
            [0, 2, 3, 1, 2, 4],
            [2, 0, 3, 2, 3, 5],
            [3, 3, 0, 2, 1, 3],
            [1, 2, 2, 0, 1, 3],
            [2, 3, 1, 1, 0, 2],
            [4, 5, 3, 3, 2, 0],
        ],
        [
            (0, 0, 1),
            (0, 0, 2),
            (0, 0, 3),
            (1, 1, 0),
            (1, 1, 2),
            (1, 1, 3),
            (2, 2, 0),
            (2, 2, 1),
            (2, 2, 3),
            (2, 2, 4),
            (2, 2, 5),
            (3, 3, 0),
            (3, 3, 1),
            (3, 3, 2),
            (3, 3, 4),
            (4, 4, 2),
            (4, 4, 3),
            (4, 4, 5),
            (5, 5, 2),
            (5, 5, 4),
            (2, 0, 4),
            (2, 0, 5),
            (2, 1, 4),
            (2, 1, 5),
            (2, 3, 5),
            (2, 4, 0),
            (2, 4, 1),
            (2, 5, 0),
            (2, 5, 1),
            (2, 5, 3),
        ],
    ), "OSPF test 1 failed"

    assert ospf_result[1] == (
        [[0, 3, 1, 4], [3, 0, 2, 5], [1, 2, 0, 3], [4, 5, 3, 0]],
        [
            (0, 0, 1),
            (0, 0, 2),
            (1, 1, 0),
            (1, 1, 2),
            (2, 2, 0),
            (2, 2, 1),
            (2, 2, 3),
            (3, 3, 2),
            (2, 0, 3),
            (2, 1, 3),
            (2, 3, 0),
            (2, 3, 1),
        ],
    ), "OSPF test 2 failed"


def test_rip():
    rip_result = [run_rip(link_cost) for link_cost in TEST_DATA]

    assert rip_result[0] == (
        [
            [0, 2, 3, 1, 2, 4],
            [2, 0, 3, 2, 3, 5],
            [3, 3, 0, 2, 1, 3],
            [1, 2, 2, 0, 1, 3],
            [2, 3, 1, 1, 0, 2],
            [4, 5, 3, 3, 2, 0],
        ],
        [
            (0, 1),
            (0, 2),
            (0, 3),
            (1, 0),
            (1, 2),
            (1, 3),
            (2, 0),
            (2, 1),
            (2, 3),
            (2, 4),
            (2, 5),
            (3, 0),
            (3, 1),
            (3, 2),
            (3, 4),
            (4, 2),
            (4, 3),
            (4, 5),
            (5, 2),
            (5, 4),
            (0, 1),
            (0, 2),
            (0, 3),
            (1, 0),
            (1, 2),
            (1, 3),
            (2, 0),
            (2, 1),
            (2, 3),
            (2, 4),
            (2, 5),
            (3, 0),
            (3, 1),
            (3, 2),
            (3, 4),
            (4, 2),
            (4, 3),
            (4, 5),
            (5, 2),
            (5, 4),
            (0, 1),
            (0, 2),
            (0, 3),
            (1, 0),
            (1, 2),
            (1, 3),
            (2, 0),
            (2, 1),
            (2, 3),
            (2, 4),
            (2, 5),
            (5, 2),
            (5, 4),
        ],
    ), "RIP test 1 failed"

    assert rip_result[1] == (
        [[0, 3, 1, 4], [3, 0, 2, 5], [1, 2, 0, 3], [4, 5, 3, 0]],
        [
            (0, 1),
            (0, 2),
            (1, 0),
            (1, 2),
            (2, 0),
            (2, 1),
            (2, 3),
            (3, 2),
            (0, 1),
            (0, 2),
            (1, 0),
            (1, 2),
            (3, 2),
        ],
    ), "RIP test 2 failed"


if __name__ == "__main__":
    main()
