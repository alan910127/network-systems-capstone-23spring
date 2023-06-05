from mininet.topo import Topo


class NetworkOneTopology(Topo):
    def build(self):
        hosts = [self.addHost("h{}".format(i)) for i in range(1, 5)]
        switch = self.addSwitch("s1")

        for host in hosts:
            self.addLink(host, switch)


class NetworkTwoTopology(Topo):
    def build(self):
        hosts = [self.addHost("h{}".format(i)) for i in range(5, 9)]
        switch = self.addSwitch("s2")

        for host in hosts:
            self.addLink(host, switch)


topos = {
    "n1topo": NetworkOneTopology,
    "n2topo": NetworkTwoTopology,
}
