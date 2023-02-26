#ifndef _NSCAP_HW1_PRINT_INFO_HPP_
#define _NSCAP_HW1_PRINT_INFO_HPP_

#include <netinet/ip.h>

#include "types.hpp"

void print_icmp_info(const iphdr* ip_header, const u8* ip_data);
void print_tcp_info(const iphdr* ip_header, const u8* ip_data);
void print_udp_info(const iphdr* ip_header, const u8* ip_data);

#endif  // !_NSCAP_HW1_PRINT_INFO_HPP_