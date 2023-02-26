#ifndef _NSCAP_HW1_TYPES_HPP_
#define _NSCAP_HW1_TYPES_HPP_

#include <iostream>
#include <variant>

using u8 = uint8_t;
using u16 = uint16_t;
using u32 = uint32_t;

template <typename T, typename E>
struct Result {
  Result(T&& value) : inner{std::move(value)} {}
  Result(E&& error) : inner{std::move(error)} {}

  auto is_ok() const -> bool { return this->inner.index() == 0; }
  auto is_err() const -> bool { return this->inner.index() == 1; }

  auto ok() -> T&& { return std::move(std::get<0>(this->inner)); }
  auto err() -> E&& { return std::move(std::get<1>(this->inner)); }

 private:
  std::variant<T, E> inner;
};

#endif  // !_NSCAP_HW1_TYPES_HPP_