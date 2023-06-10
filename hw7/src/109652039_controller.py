from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import ethernet, packet
from ryu.ofproto import ether, inet, ofproto_v1_3

DROPPED_PORTS = (3, 4)


class Tables:
    """All the table IDs in the controller."""

    DEFAULT = 0
    FILTER_ICMP = 1
    FILTER_PORT = 2
    FORWARD = 3


class Priority:
    """Represents different prorities for matching rules."""

    HIGH = 10
    MEDIUM = 5
    LOW = 0


class CustomController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(CustomController, self).__init__(*args, **kwargs)
        # initialize mac address table.
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.add_default_table_flow(datapath, ofproto, parser)
        self.add_filter_icmp_table_flow(datapath, ofproto, parser)
        self.add_filter_port_table_flow(datapath, ofproto, parser)
        self.add_forward_table_flow(datapath, ofproto, parser)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # get Datapath ID to identify OpenFlow switches.
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # analyse the received packets using the packet library.
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src

        # get the received port number from packet_in message.
        in_port = msg.match["in_port"]

        self.logger.info(f"packet in {dpid} {src} {dst} {in_port}")

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        # if the destination mac address is already learned,
        # decide which port to output the packet, otherwise FLOOD.
        out_port = self.mac_to_port[dpid].get(dst, ofproto.OFPP_FLOOD)

        # construct action list.
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time.
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        # construct packet_out message and send it.
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=msg.data,
        )
        datapath.send_msg(out)

    def add_default_table_flow(self, datapath, ofproto, parser):
        # default table ----> filter 1
        match = parser.OFPMatch()
        self.add_change_table_flow(
            datapath,
            Priority.HIGH,
            match,
            src_table=Tables.DEFAULT,
            dst_table=Tables.FILTER_ICMP,
        )

    def add_filter_icmp_table_flow(self, datapath, ofproto, parser):
        match = parser.OFPMatch(
            eth_type=ether.ETH_TYPE_IP,
            ip_proto=inet.IPPROTO_ICMP,
        )
        self.add_change_table_flow(
            datapath,
            Priority.HIGH,
            match,
            src_table=Tables.FILTER_ICMP,
            dst_table=Tables.FILTER_PORT,
        )

        match = parser.OFPMatch()
        self.add_change_table_flow(
            datapath,
            Priority.MEDIUM,
            match,
            src_table=Tables.FILTER_ICMP,
            dst_table=Tables.FORWARD,
        )

    def add_filter_port_table_flow(self, datapath, ofproto, parser):
        for port in DROPPED_PORTS:
            match = parser.OFPMatch(in_port=port)
            self.add_drop_packet_flow(
                datapath,
                Priority.HIGH,
                match,
                table=Tables.FILTER_PORT,
            )

        match = parser.OFPMatch()
        self.add_change_table_flow(
            datapath,
            Priority.MEDIUM,
            match,
            src_table=Tables.FILTER_PORT,
            dst_table=Tables.FORWARD,
        )

    def add_forward_table_flow(self, datapath, ofproto, parser):
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, Priority.LOW, match, actions, table=Tables.FORWARD)

    def add_flow(self, datapath, priority, match, actions, table: int = Tables.DEFAULT):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            table_id=table,
        )
        datapath.send_msg(mod)

    def add_change_table_flow(
        self, datapath, priority, match, src_table: int, dst_table: int
    ):
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionGotoTable(table_id=dst_table)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            table_id=src_table,
        )
        datapath.send_msg(mod)

    def add_drop_packet_flow(self, datapath, priority, match, table: int):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_CLEAR_ACTIONS, [])]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            table_id=table,
        )
        datapath.send_msg(mod)
