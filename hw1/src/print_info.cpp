#include "print_info.hpp"

#include <arpa/inet.h>
#include <netinet/ip_icmp.h>
#include <netinet/tcp.h>
#include <netinet/udp.h>

#include <iomanip>
#include <iostream>

constexpr int UDP_HEADER_LENGTH = sizeof(udphdr);

std::string ip_to_string(u32 address) {
  char buf[INET_ADDRSTRLEN]{};
  return inet_ntop(AF_INET, &address, buf, INET_ADDRSTRLEN);
}

void print_ip_info(const std::string& transport_type, u32 source_ip,
                   u32 dest_ip) {
  std::cout << std::endl;
  std::cout << "Transport type: " << transport_type << std::endl;
  std::cout << "Source IP: " << ip_to_string(source_ip) << std::endl;
  std::cout << "Destination IP: " << ip_to_string(dest_ip) << std::endl;
}

void print_icmp_info(const iphdr* ip_header, const u8* ip_data) {
  auto icmp_header = reinterpret_cast<const icmphdr*>(ip_data);

  print_ip_info("ICMP", ip_header->saddr, ip_header->daddr);
  std::cout << "ICMP type value: " << static_cast<u32>(icmp_header->type)
            << std::endl;
}

void print_transport_info(u16 source_port, u16 dest_port, const u8* payload,
                          int length) {
  std::cout << "Source port: " << ntohs(source_port) << std::endl;
  std::cout << "Destination port: " << ntohs(dest_port) << std::endl;
  std::cout << "Payload:";
  for (int i = 0; i < std::min(length, 16); ++i) {
    std::cout << ' ' << std::hex << std::setw(2) << std::setfill('0')
              << static_cast<u32>(payload[i]);
  }
  std::cout << std::dec << std::endl;
}

void print_tcp_info(const iphdr* ip_header, const u8* ip_data) {
  auto tcp_header = reinterpret_cast<const tcphdr*>(ip_data);
  auto tcp_header_length = tcp_header->doff * 4;

  auto tcp_data = reinterpret_cast<const u8*>(tcp_header) + tcp_header_length;
  auto tcp_data_length =
      ntohs(ip_header->tot_len) - (ip_header->ihl * 4) - tcp_header_length;

  print_ip_info("TCP", ip_header->saddr, ip_header->daddr);
  print_transport_info(tcp_header->source, tcp_header->dest, tcp_data,
                       tcp_data_length);
}

void print_udp_info(const iphdr* ip_header, const u8* ip_data) {
  auto udp_header = reinterpret_cast<const udphdr*>(ip_data);
  auto udp_packet_size = ntohs(udp_header->len);
  auto udp_data = reinterpret_cast<const u8*>(udp_header) + UDP_HEADER_LENGTH;
  auto udp_data_length = udp_packet_size - UDP_HEADER_LENGTH;

  print_ip_info("UDP", ip_header->saddr, ip_header->daddr);
  print_transport_info(udp_header->source, udp_header->dest, udp_data,
                       udp_data_length);
}
