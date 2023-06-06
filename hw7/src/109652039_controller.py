from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import ethernet, packet, ether_types, in_proto
from ryu.ofproto import ofproto_v1_3, ether


class MyController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    TABLE_DEFAULT = 0
    TABLE_FILTER_1 = 1
    TABLE_FILTER_2 = 2
    TABLE_FORWARD = 3

    def __init__(self, *args, **kwargs):
        super(MyController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        self.logger.info("HERE switch features handler")
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

        self.add_default_table(datapath)
        self.add_filter_table_1(datapath)
        self.add_filter_table_2(datapath)
        self.apply_filter_table_1_rules(datapath)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Construct flow_mod message and send it
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]

        if buffer_id:
            mod = parser.OFPFlowMod(
                datapath=datapath, 
                buffer_id=buffer_id,
                priority=priority, 
                table_id=self.TABLE_FORWARD,                   
                match=match, 
                instructions=inst,
            )
        else:
            mod = parser.OFPFlowMod(
                datapath=datapath, 
                priority=priority, 
                table_id=self.TABLE_FORWARD,                   
                match=match, 
                instructions=inst,
            )

        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        in_port = msg.match['in_port']
        if msg.table_id == self.TABLE_FILTER_2 and in_port in (3, 4):
            # drop the packets
            return

        # forward the packet
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src

        self.logger.info(f"packet in {dpid} {src} {dst} {in_port}")

        # learn a mac address to avoid FLOOD next time
        self.mac_to_port[dpid][src] = in_port

        # if the destination mac address is already learned,
        # decide which port to output the packet, otherwise FLOOD
        out_port = self.mac_to_port[dpid].get(dst, ofproto.OFPP_FLOOD)

        # construct action list
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
        
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return

            self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data     

        # construct packet_out message and send it
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    def add_default_table(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionGotoTable(self.TABLE_FILTER_1)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=self.TABLE_DEFAULT, instructions=inst)
        datapath.send_msg(mod)

    def add_filter_table_1(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionGotoTable(self.TABLE_FORWARD)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=self.TABLE_FILTER_1, priority=1, instructions=inst)
        datapath.send_msg(mod)
    
    def apply_filter_table_1_rules(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=in_proto.IPPROTO_ICMP)
        inst = [parser.OFPInstructionGotoTable(self.TABLE_FILTER_2)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=self.TABLE_FILTER_1, priority=10000, match=match, instructions=inst)
        datapath.send_msg(mod)

    def add_filter_table_2(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionGotoTable(self.TABLE_FORWARD)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=self.TABLE_FILTER_2, priority=1, instructions=inst)
        datapath.send_msg(mod)        
