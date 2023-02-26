
#include <getopt.h>
#include <netinet/ether.h>
#include <netinet/ip.h>

#include <iostream>

#include "pcap.hpp"
#include "print_info.hpp"

#define ANY_PACKET "udp or tcp or icmp"
#define dbg(x)                                  \
  do {                                          \
    std::cerr << #x << " = " << x << std::endl; \
  } while (0)

struct CliArgs {
  std::string interface_name;
  std::string packet_filter = ANY_PACKET;
  int capture_count = -1;
};

CliArgs parse_args(int argc, char* const* argv);
bool handle_packet(const u8* packet);

int main(int argc, char* const argv[]) {
  auto [interface_name, packet_filter, capture_count] = parse_args(argc, argv);

  if (interface_name.empty()) {
    std::cerr << "wrong command" << std::endl;
    std::exit(EXIT_FAILURE);
  }

  auto devices_result = nscap::InternetDevices::init();
  if (devices_result.is_err()) {
    std::cerr << "pcap_findalldevs: " << devices_result.err() << std::endl;
    std::exit(EXIT_FAILURE);
  }

  auto devices = devices_result.ok();

  for (auto device : devices) {
    std::cout << "Name: " << device->name << std::endl;
  }

  auto capture_result = nscap::DeviceCapture::open(interface_name);
  if (capture_result.is_err()) {
    std::cerr << "pcap_open_live(): " << capture_result.err() << std::endl;
    std::exit(EXIT_FAILURE);
  }
  auto capture = capture_result.ok();

  capture.compile(packet_filter)
      .set_filter()
      .set_handler(handle_packet)
      .loop(capture_count);

  if (!capture) {
    capture.print_error();
    std::exit(EXIT_FAILURE);
  }

  return 0;
}

CliArgs parse_args(int argc, char* const* argv) {
  const char* optstr = "i:c:f:";
  const option opts[] = {{"interface", 1, nullptr, 'i'},
                         {"count", 1, nullptr, 'c'},
                         {"filter", 1, nullptr, 'f'}};

  CliArgs args;

  char opt;
  while ((opt = getopt_long(argc, argv, optstr, opts, nullptr)) != -1) {
    switch (opt) {
      case 'i': {
        args.interface_name = optarg;
        break;
      }
      case 'c': {
        args.capture_count = std::stoi(optarg);
        break;
      }
      case 'f': {
        args.packet_filter = optarg;

        if (args.packet_filter == "all") {
          args.packet_filter = ANY_PACKET;
        }
        break;
      }
    }
  }

  return args;
}

bool handle_packet(const u8* packet) {
  if (packet == nullptr) return false;

  auto ethernet_header = reinterpret_cast<const ether_header*>(packet);
  if (ntohs(ethernet_header->ether_type) != ETHERTYPE_IP) return false;

  auto ip_header = reinterpret_cast<const iphdr*>(
      reinterpret_cast<const u8*>(ethernet_header) + sizeof(ether_header));

  auto ip_data = reinterpret_cast<const u8*>(ip_header) + ip_header->ihl * 4;

  switch (ip_header->protocol) {
    case IPPROTO_ICMP: {
      print_icmp_info(ip_header, ip_data);
      break;
    }
    case IPPROTO_TCP: {
      print_tcp_info(ip_header, ip_data);
      break;
    }
    case IPPROTO_UDP: {
      print_udp_info(ip_header, ip_data);
      break;
    }
    default: {
      std::cout << "Unexpected transport type: "
                << static_cast<u32>(ip_header->protocol) << std::endl;
      return false;
    }
  }

  return true;
}
