#ifndef _NSCAP_HW1_PCAP_HPP_
#define _NSCAP_HW1_PCAP_HPP_

#include <pcap/pcap.h>

#include <functional>
#include <optional>
#include <string>
#include <variant>
#include <vector>

#include "types.hpp"

namespace nscap {

class InternetDevices {
 public:
  InternetDevices(InternetDevices&& other);
  ~InternetDevices();

  static auto init() -> Result<InternetDevices, std::string>;
  auto begin() -> std::vector<pcap_if_t*>::iterator;
  auto end() -> std::vector<pcap_if_t*>::iterator;

 private:
  InternetDevices(std::vector<pcap_if_t*>&& devices);
  std::vector<pcap_if_t*> devices;
};

class DeviceCapture {
 public:
  using Handler = std::function<bool(const u_char* packet)>;

  static auto open(const std::string& interface_name)
      -> Result<DeviceCapture, std::string>;

  DeviceCapture();
  DeviceCapture(DeviceCapture&& other);
  ~DeviceCapture();

  auto is_valid() const -> bool;
  operator bool() const;

  auto compile(const std::string& filter) -> DeviceCapture&;
  auto set_filter() -> DeviceCapture&;

  auto set_handler(Handler fn) -> DeviceCapture&;

  auto loop(int loop_count = -1) -> DeviceCapture&;

  auto print_error() -> void;

 private:
  pcap_t* handle;
  bpf_program fp;
  Handler fn;
  std::optional<std::string> error;
};

}  // namespace nscap

#endif  // !_NSCAP_HW1_PCAP_HPP_