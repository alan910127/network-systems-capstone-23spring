from main import run_ospf, run_rip

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
