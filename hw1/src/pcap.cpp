#include "pcap.hpp"

#include <iostream>

namespace nscap {

InternetDevices::InternetDevices(InternetDevices&& other)
    : devices{std::move(other.devices)} {}

InternetDevices::InternetDevices(std::vector<pcap_if_t*>&& devices)
    : devices(std::move(devices)) {}

InternetDevices::~InternetDevices() {
  if (!this->devices.empty()) {
    pcap_freealldevs(this->devices.front());
  }
}

auto InternetDevices::init() -> Result<InternetDevices, std::string> {
  pcap_if_t* device_list = nullptr;
  char errbuf[PCAP_ERRBUF_SIZE]{};

  if (pcap_findalldevs(&device_list, errbuf) < 0) {
    return std::string{errbuf};
  }

  std::vector<pcap_if_t*> devices;
  for (auto device = device_list; device != nullptr; device = device->next) {
    devices.push_back(device);
  }

  return InternetDevices{std::move(devices)};
}

auto InternetDevices::begin() -> std::vector<pcap_if_t*>::iterator {
  return this->devices.begin();
}

auto InternetDevices::end() -> std::vector<pcap_if_t*>::iterator {
  return this->devices.end();
}

auto DeviceCapture::open(const std::string& interface_name)
    -> Result<DeviceCapture, std::string> {
  char errbuf[PCAP_ERRBUF_SIZE]{};
  auto capture = DeviceCapture{};

  capture.handle = pcap_open_live(interface_name.c_str(), 65535, 1, 1, errbuf);
  if (capture.handle == nullptr) {
    return std::string{errbuf};
  }
  return capture;
}

DeviceCapture::DeviceCapture() : handle{} {}
DeviceCapture::DeviceCapture(DeviceCapture&& other)
    : handle{other.handle}, fp{other.fp} {
  other.handle = nullptr;
  other.fp = bpf_program{};
  this->fn.swap(other.fn);
}
DeviceCapture::~DeviceCapture() {
  if (this->handle != nullptr) (this->handle);
}

auto DeviceCapture::is_valid() const -> bool {
  return !this->error.has_value();
}

DeviceCapture::operator bool() const { return this->is_valid(); }

auto DeviceCapture::compile(const std::string& packet_filter)
    -> DeviceCapture& {
  if (!this->is_valid()) return *this;

  int retval = pcap_compile(this->handle, &this->fp, packet_filter.c_str(), 1,
                            PCAP_NETMASK_UNKNOWN);

  if (retval < 0) {
    this->error.emplace("pcap_compile");
  }
  return *this;
}

auto DeviceCapture::set_filter() -> DeviceCapture& {
  if (!this->is_valid()) return *this;

  int retval = pcap_setfilter(this->handle, &this->fp);

  if (retval < 0) {
    this->error.emplace("pcap_setfilter");
  }
  return *this;
}

auto DeviceCapture::set_handler(Handler fn) -> DeviceCapture& {
  if (!this->is_valid()) return *this;
  this->fn = fn;
  return *this;
}

auto DeviceCapture::loop(int loop_count) -> DeviceCapture& {
  if (!this->is_valid()) return *this;

  pcap_pkthdr header;
  bool is_infinite = loop_count < 0;

  for (int i = 0; is_infinite || i < loop_count;) {
    const u_char* packet = pcap_next(this->handle, &header);
    if (this->fn(packet)) ++i;
  }

  return *this;
}

auto DeviceCapture::print_error() -> void {
  if (this->error.has_value())
    pcap_perror(this->handle, this->error.value().c_str());
}

}  // namespace nscap