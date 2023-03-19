from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Protocol

import setting
from typing_extensions import Self

IpAddress = str
MacAddress = str
PortNumber = int

BROADCAST_MAC = "ffff"

logger = logging.getLogger(__name__)


class PacketType(Enum):
    ARP = auto()
    ICMP_REQUEST = auto()
    ICMP_REPLY = auto()


@dataclass
class Packet:
    type: PacketType
    source_name: str
    source_ip: IpAddress
    source_mac: MacAddress
    destination_ip: IpAddress
    destination_mac: MacAddress


class NetworkDevice(Protocol):
    name: str

    def add(self, node: Self) -> None:
        """Link with another network device"""

    def show_table(self):
        """Show the ARP or MAC table"""

    def clear(self):
        """Clear the ARP or MAC table"""

    def handle_packet(self, packet: Packet):
        """Handle the incoming packet"""


@dataclass
class Host:
    name: str
    ip: IpAddress
    mac: MacAddress
    port_to: Optional[NetworkDevice] = None
    arp_table: dict[IpAddress, MacAddress] = field(default_factory=dict)

    def add(self, node: NetworkDevice):
        self.port_to = node

    def show_table(self):
        """Display ARP table entries for this host"""

        print("ip : mac")
        print(f"---------------{self.name}:")

        for host_ip, host_mac in self.arp_table.items():
            print(f"{host_ip} : {host_mac}")

    def clear(self):
        """Clear ARP table entries for this host"""

        self.arp_table.clear()

    def update_arp(self, ip: IpAddress, mac: MacAddress):
        """Update ARP table with a new entry"""

        self.arp_table[ip] = mac

    def handle_packet(self, packet: Packet):
        """Handle incoming packets"""

        if packet.destination_mac not in (self.mac, BROADCAST_MAC):
            return

        if packet.type == PacketType.ICMP_REPLY:
            return

        if packet.type == PacketType.ARP:
            # update the ARP table
            self.update_arp(packet.source_ip, packet.source_mac)

            if (
                packet.destination_mac != BROADCAST_MAC
                or packet.destination_ip != self.ip
            ):
                return

            # send ARP reply to the source
            arp_packet = Packet(
                type=PacketType.ARP,
                source_name=self.name,
                source_ip=self.ip,
                source_mac=self.mac,
                destination_ip=packet.source_ip,
                destination_mac=packet.source_mac,
            )
            return self.send(arp_packet)

        # this is an ICMP request, send an ICMP reply to the source
        icmp_packet = Packet(
            type=PacketType.ICMP_REPLY,
            source_name=self.name,
            source_ip=self.ip,
            source_mac=self.mac,
            destination_ip=packet.source_ip,
            destination_mac=packet.source_mac,
        )
        self.send(icmp_packet)

    def ping(self, dest_ip: IpAddress):
        """Send a ping request"""

        if dest_ip not in self.arp_table:
            # send an ARP request
            arp_packet = Packet(
                type=PacketType.ARP,
                source_name=self.name,
                source_ip=self.ip,
                source_mac=self.mac,
                destination_ip=dest_ip,
                destination_mac=BROADCAST_MAC,
            )
            self.send(arp_packet)

        dest_mac = self.arp_table[dest_ip]

        # send an ICMP request to the destination
        icmp_packet = Packet(
            type=PacketType.ICMP_REQUEST,
            source_name=self.name,
            source_ip=self.ip,
            source_mac=self.mac,
            destination_ip=dest_ip,
            destination_mac=dest_mac,
        )
        self.send(icmp_packet)

    def send(self, packet: Packet):
        if self.port_to is None:
            logging.error(f"Host {self.name} has no port to send packets")
            return

        logging.debug(
            f"{self.name} sends an {packet.type.name} packet to {packet.destination_ip}"
        )

        self.port_to.handle_packet(packet)


@dataclass
class Switch:
    name: str
    mac_table: dict[MacAddress, PortNumber] = field(default_factory=dict)
    port_to: list[NetworkDevice] = field(default_factory=list)

    def add(self, node: NetworkDevice):
        self.port_to.append(node)

    def show_table(self):
        """Display MAC table entries for this switch"""

        print("mac : port")
        print(f"---------------{self.name}:")

        for mac, port in self.mac_table.items():
            print(f"{mac} : {port}")

    def clear(self):
        """Clear MAC table entries for this switch"""

        self.mac_table.clear()

    def update_mac(self, mac_address: MacAddress, from_port: PortNumber):
        """Update MAC table with a new entry"""

        self.mac_table[mac_address] = from_port

    def get_port_by_name(self, name: str):
        return next(i for i, node in enumerate(self.port_to) if node.name == name)

    def send_to_ports(self, packet: Packet, exclude: PortNumber):
        for i, _ in enumerate(self.port_to):
            if i == exclude:
                continue

            self.send(i, packet)

    def handle_packet(self, packet: Packet):
        """Handle incoming packets"""

        source_port = self.get_port_by_name(packet.source_name)

        self.update_mac(packet.source_mac, source_port)

        if packet.type == PacketType.ARP:
            # broadcast the packet
            return self.send_to_ports(packet, exclude=source_port)

        destination_port = self.mac_table.get(packet.destination_mac)

        if destination_port is None:
            # flood the packet
            return self.send_to_ports(packet, exclude=source_port)

        self.send(destination_port, packet)

    def send(self, index: PortNumber, packet: Packet):
        """Send to the specific port"""

        packet.source_name = self.name
        self.port_to[index].handle_packet(packet)


def create_link(node1: NetworkDevice, node2: NetworkDevice):
    """Create a link between two nodes"""

    node1.add(node2)
    node2.add(node1)


class Net:
    def __init__(
        self,
        hosts: list[str],
        switches: list[str],
        links: list[tuple[str, str]],
        ip_table: dict[str, IpAddress],
        mac_table: dict[str, MacAddress],
    ):
        self.host_dict: dict[str, Host] = {
            host_name: Host(
                name=host_name,
                ip=ip_table[host_name],
                mac=mac_table[host_name],
            )
            for host_name in hosts
        }

        self.switch_dict: dict[str, Switch] = {
            switch_name: Switch(name=switch_name) for switch_name in switches
        }

        for (name1, name2) in links:
            node1 = (
                self.host_dict[name1]
                if name1 in self.host_dict
                else self.switch_dict[name1]
            )
            node2 = (
                self.host_dict[name2]
                if name2 in self.host_dict
                else self.switch_dict[name2]
            )

            create_link(node1, node2)

    @classmethod
    def from_setting(cls):
        hostlist = setting.get_hosts().split()
        switchlist = setting.get_switches().split()
        link_command = setting.get_links().split()
        ip_table = setting.get_ip()
        mac_table = setting.get_mac()

        links = [tuple(link.split(",")) for link in link_command]
        logging.debug(links)

        return cls(
            hosts=hostlist,
            switches=switchlist,
            links=links,
            ip_table=ip_table,
            mac_table=mac_table,
        )

    def _get_node(self, name: str):
        return self.host_dict.get(name) or self.switch_dict.get(name)

    def _handle_command(self, command: str):
        match command.split():
            case [name1, "ping", name2]:
                self.ping(name1, name2)

            case ["show_table", target]:
                self.show_table(target)

            case ["clear", name]:
                self.clear(name)

            case _:
                print("a wrong command")

    def run(self):
        """Run the simulation"""

        while True:
            command = input(">> ")
            self._handle_command(command)

    def ping(self, node1: str, node2: str):
        """Initiate a ping between two hosts"""

        host1 = self.host_dict.get(node1)
        host2 = self.host_dict.get(node2)

        if host1 is None or host2 is None:
            logging.error(f"Invalid hosts: {node1}, {node2}")
            return

        host1.ping(host2.ip)

    def show_table(self, target: str):
        """Display the ARP or MAC table of the given nodes"""

        match target:
            case "all_hosts":
                for host in self.host_dict.values():
                    host.show_table()

            case "all_switches":
                for switch in self.switch_dict.values():
                    switch.show_table()

            case name:
                if (node := self._get_node(name)) is not None:
                    node.show_table()

    def clear(self, target: str):
        """Clear the ARP or MAC table of a node"""

        if (node := self._get_node(target)) is not None:
            node.clear()


def main():
    logging.basicConfig(level=logging.DEBUG)
    net = Net.from_setting()
    net.run()


if __name__ == "__main__":
    main()
