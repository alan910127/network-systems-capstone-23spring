import protocols
from setting import Setting


def create_setting() -> Setting:
    return Setting(
        host_num=3,
        total_time=100,
        packet_num=4,
        max_colision_wait_time=20,
        p_resend=0.3,
        packet_size=3,
        link_delay=1,
        seed=4,
    )


def main() -> None:
    for protocol in (
        protocols.aloha,
        # protocols.slotted_aloha,
        # protocols.csma,
        # protocols.csma_cd,
    ):
        success_rate, idle_rate, collision_rate = protocol(create_setting(), True)
        print(f"{protocol.__name__}:")
        print(f"success_rate: {success_rate:.2f}")
        print(f"idle_rate: {idle_rate:.2f}")
        print(f"collision_rate: {collision_rate:.2f}")
        print()


if __name__ == "__main__":
    main()
