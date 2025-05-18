####################################################
# DVrouter.py
# Name: 
# HUID: 
#####################################################
from router import Router
from packet import Packet 
import json

class DVrouter(Router):
    """Distance vector routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    INFINITY = 16 

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_periodic_update_time = 0

        # dictionary thể hiện vector khoảng cách của chính router này: {destination_addr: cost}
        self.dv = {self.addr: 0}
        
        # dictionary xác định cổng ra nào sẽ được sử dụng để gửi một gói tin đến một đích cụ thể: {destination_addr: outgoing_port}
        self.forwarding_table = {self.addr: -1} # -1 for self
        
        # dictionary ánh xạ mỗi đích tới địa chỉ của router hàng xóm
        self.next_hop_for_dest = {self.addr: self.addr}
        
        # dictionary chứa chi phí của các liên kết trực tiếp từ router này đến các router hàng xóm của nó: {neighbor_addr: cost}
        self.neighbor_link_costs = {}
        
        # dictionary ánh xạ địa chỉ của một router hàng xóm sang số cổng cục bộ
        self.neighbor_ports = {}
        
        # dictionary ánh xạ cổng cục bộ sang hàng xóm
        self.port_to_neighbor = {}
        
        # dictionary lưu trữ các vector khoảng cách (DV) gần nhất mà router này đã nhận được từ mỗi hàng xóm của nó.
        # đây là một dictionary lồng nhau. {neighbor_addr: {destination_addr: cost}}
        self.neighbor_dvs = {}

        # tập hợp chứa địa chỉ của tất cả các router (đích) mà router này đã từng nghe nói đến trong mạng
        self.all_known_destinations = {self.addr}

    def _send_dv_to_all_neighbors(self):
        """
        Gửi DV hiện tại của router này (self.dv) đến tất cả các router hàng xóm trực tiếp. 
        Hàm này triển khai kỹ thuật "Split Horizon with Poisoned Reverse".
        """
        for neighbor_addr, port in self.neighbor_ports.items():
            dv_to_send_to_neighbor = {}
            for dest, cost in self.dv.items():
                if self.next_hop_for_dest.get(dest) == neighbor_addr and dest != neighbor_addr:
                    dv_to_send_to_neighbor[dest] = self.INFINITY
                else:
                    dv_to_send_to_neighbor[dest] = cost

            if self.addr not in dv_to_send_to_neighbor or dv_to_send_to_neighbor[self.addr] == self.INFINITY :
                 dv_to_send_to_neighbor[self.addr] = 0

            packet_content = json.dumps(dv_to_send_to_neighbor)
            dv_packet = Packet(kind=Packet.ROUTING, src_addr=self.addr, dst_addr=neighbor_addr, content=packet_content)
            self.send(port, dv_packet)

    def _recompute_routes(self):
        """
        Tính toán lại toàn bộ vector khoảng cách (self.dv), bảng chặng kế tiếp (self.next_hop_for_dest), và bảng chuyển tiếp (self.forwarding_table) 
        của router dựa trên thông tin chi phí liên kết trực tiếp (self.neighbor_link_costs) và các DV đã nhận từ hàng xóm (self.neighbor_dvs)
        """
        changed = False
        new_dv = {}
        new_next_hop = {} 
        for dest in self.all_known_destinations:
            new_dv[dest] = self.INFINITY
        new_dv[self.addr] = 0
        new_next_hop[self.addr] = self.addr

        for dest_addr in self.all_known_destinations:
            if dest_addr == self.addr:
                continue
            min_cost_to_dest = self.INFINITY
            best_next_hop_neighbor = None

            # Option 1: Qua liên kết trực tiếp (nếu dest_addr là hàng xóm)
            if dest_addr in self.neighbor_link_costs:
                direct_cost = self.neighbor_link_costs[dest_addr]
                if direct_cost < min_cost_to_dest:
                    min_cost_to_dest = direct_cost
                    best_next_hop_neighbor = dest_addr

            # Option 2: Qua các router hàng xóm khác
            for neighbor, received_dv_from_neighbor in self.neighbor_dvs.items():
                if neighbor not in self.neighbor_link_costs: 
                    continue
                cost_to_neighbor = self.neighbor_link_costs[neighbor]
                cost_neighbor_to_dest = received_dv_from_neighbor.get(dest_addr, self.INFINITY)
                total_cost_via_neighbor = cost_to_neighbor + cost_neighbor_to_dest
                if total_cost_via_neighbor >= self.INFINITY:
                    total_cost_via_neighbor = self.INFINITY
                if total_cost_via_neighbor < min_cost_to_dest:
                    min_cost_to_dest = total_cost_via_neighbor
                    best_next_hop_neighbor = neighbor 
            
            new_dv[dest_addr] = min_cost_to_dest
            if best_next_hop_neighbor is not None:
                new_next_hop[dest_addr] = best_next_hop_neighbor

        if new_dv != self.dv or new_next_hop != self.next_hop_for_dest:
            changed = True
            self.dv = new_dv
            self.next_hop_for_dest = new_next_hop
            # Update forwarding table dựa trên new_next_hop
            current_ft = {self.addr: -1}
            for dest, next_hop_n in self.next_hop_for_dest.items():
                if dest == self.addr:
                    continue
                if self.dv.get(dest, self.INFINITY) < self.INFINITY : # Có đường đi
                    # Nếu next_hop_n là hàng xóm trực tiếp thì dùng port của hàng xóm này.
                    if next_hop_n in self.neighbor_ports:
                         current_ft[dest] = self.neighbor_ports[next_hop_n]
            if self.forwarding_table != current_ft:
                self.forwarding_table = current_ft
                
        return changed

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            if packet.dst_addr == self.addr: 
                return
            if packet.dst_addr in self.forwarding_table:
                out_port = self.forwarding_table[packet.dst_addr]
                if out_port != -1 and out_port is not None: 
                    self.send(out_port, packet)
        else: 
            try:
                received_dv = json.loads(packet.content)
                sender_addr = packet.src_addr 
            except (json.JSONDecodeError, KeyError):
                return 
            if sender_addr not in self.neighbor_link_costs:
                 return 
            for dest in received_dv.keys():
                self.all_known_destinations.add(dest)
            self.neighbor_dvs[sender_addr] = received_dv
            if self._recompute_routes():
                self._send_dv_to_all_neighbors()

    def handle_new_link(self, port, endpoint_addr, cost):
        """Handle new link."""
        self.neighbor_link_costs[endpoint_addr] = cost
        self.neighbor_ports[endpoint_addr] = port
        self.port_to_neighbor[port] = endpoint_addr
        self.all_known_destinations.add(endpoint_addr)
        
        self.neighbor_dvs[endpoint_addr] = {} 
        if self._recompute_routes():
            self._send_dv_to_all_neighbors()
        else:
            self._send_dv_to_all_neighbors()

    def handle_remove_link(self, port):
        """Handle removed link."""
        if port not in self.port_to_neighbor:
            return 
        removed_neighbor_addr = self.port_to_neighbor.pop(port)
        if removed_neighbor_addr in self.neighbor_link_costs:
            del self.neighbor_link_costs[removed_neighbor_addr]
        if removed_neighbor_addr in self.neighbor_ports:
            del self.neighbor_ports[removed_neighbor_addr]
        if removed_neighbor_addr in self.neighbor_dvs:
            del self.neighbor_dvs[removed_neighbor_addr]

        if self._recompute_routes():
            self._send_dv_to_all_neighbors()


    def handle_time(self, time_ms):
        """Handle current time for periodic DV broadcast."""
        if time_ms - self.last_periodic_update_time >= self.heartbeat_time:
            self.last_periodic_update_time = time_ms
            if self._recompute_routes(): 
                 self._send_dv_to_all_neighbors()
            else: 
                 self._send_dv_to_all_neighbors()


    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return (f"DVrouter(addr={self.addr}, "
                f"DV={self.dv}, \n"
                f"FT={self.forwarding_table}, \n" ")"
               )