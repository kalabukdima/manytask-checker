#include <catch2/catch_test_macros.hpp>

#include "sum.h"

TEST_CASE("Private") {
    CHECK(Sum(2'000'000'000, 2'000'000'000) == 4'000'000'000LL);
    CHECK(Sum(std::numeric_limits<int64_t>::max(), std::numeric_limits<int64_t>::min()) == -1);
}
