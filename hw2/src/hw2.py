import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

import setting

if TYPE_CHECKING:
    from typing import Optional, Self

    Ip = str
    Mac = str
    Port = int

BROADCAST_MAC = "ffff"


class NetworkDevice(Protocol):
    def add(self, node: Self) -> None:
        """Link with another network device"""

    def show_table(self):
        """Show the ARP or MAC table"""

    def clear(self):
        """Clear the ARP or MAC table"""

    def handle_packet(self, dest_mac: str):
        """Handle the incoming packet"""


@dataclass
class Host:
    name: str
    ip: Ip
    mac: Mac
    port_to: Optional[NetworkDevice] = None
    arp_table: dict[Ip, Mac] = field(default_factory=dict)

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

    def update_arp(self, ip: Ip, mac: Mac):
        """Update ARP table with a new entry"""

        self.arp_table[ip] = mac

    def handle_packet(self, dest_mac: Mac):
        """Handle incoming packets"""
        # TODO: handle packet

    def ping(self, dest_ip: Ip):
        """Handle a ping request"""
        # TODO: handle ping

    def send(self):
        if self.port_to is None:
            logging.error(f"Host {self.name} has no port to send packets")
            return

        # TODO: fill in parameters
        self.port_to.handle_packet("")


@dataclass
class Switch:
    name: str
    num_ports: int
    mac_table: dict[Mac, Port] = field(default_factory=dict)
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

    def update_mac(self, mac_address: Mac, from_port: Port):
        """Update MAC table with a new entry"""

        self.mac_table[mac_address] = from_port

    def handle_packet(self, dest_mac: Mac):
        """Handle incoming packets"""
        # TODO: handle packet

    def send(self, index: Port):
        """Send to the specific port"""

        # TODO: fill in parameters
        self.port_to[index].handle_packet("")


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
        ip_table: dict[str, Ip],
        mac_table: dict[str, Mac],
    ):
        self.host_dict = {
            host_name: Host(
                name=host_name,
                ip=ip_table[host_name],
                mac=mac_table[host_name],
            )
            for host_name in hosts
        }

        self.switch_dict = {
            switch_name: Switch(name=switch_name, num_ports=3)
            for switch_name in switches
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
        link_command = setting.get_links()
        ip_table = setting.get_ip()
        mac_table = setting.get_mac()

        links = [tuple(link.split(",")) for link in link_command]

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

        if node1 not in self.host_dict or node2 not in self.host_dict:
            logging.error(f"Invalid hosts: {node1}, {node2}")
            return

        host1 = self.host_dict[node1]
        host2 = self.host_dict[node2]
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
    net = Net.from_setting()
    net.run()


if __name__ == "__main__":
    main()
