import random
from typing import Optional


class Setting:
    def __init__(
        self,
        host_num: int = 3,
        total_time: int = 10000,
        packet_num: int = 500,
        packet_size: int = 5,
        max_colision_wait_time: int = 20,
        p_resend: float = 0.3,
        link_delay: int = 1,
        seed: Optional[int] = None,
    ) -> None:
        self.host_num = host_num
        """Number of hosts."""

        self.total_time = total_time
        """Total simulation duration, 1 as the smallest unit."""

        self.packet_num = packet_num
        """Number of generated packets for each host."""

        self.packet_time = packet_size + 2 * link_delay
        """Time needed to finish each packet, equal to `slot size` in slotted ALOHA.
        
        Including the link delay for sending packet and waiting for ACK.
        Suppose that the time needed to wait for ACK is equal to link delay. 
        """

        self.max_colision_wait_time = max_colision_wait_time
        """The maximum wait time for ALOHA, CSMA and CSMA/cD to resend a packet."""

        self.p_resend = p_resend
        """The probability of resending a packet when a slot starts in slotted ALOHA."""

        self.link_delay = link_delay

        self.seed = random.randint(1, 10000) if seed is None else seed
        """Seed for random number generator."""

    # hosts產生封包的時間
    # e.g.
    #   [[10, 20, 30], # host 0
    #    [20, 30, 50], # host 1
    #    [30, 50, 60]] # host 2
    def gen_packets(self):
        def generate_for_host():
            max_timepoint = self.total_time - self.packet_time
            timepoints = random.sample(range(1, max_timepoint), self.packet_num)
            return sorted(timepoints)

        random.seed(self.seed)
        packets = [generate_for_host() for _ in range(self.host_num)]
        return packets
