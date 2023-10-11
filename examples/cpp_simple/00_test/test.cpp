#include <catch2/catch_test_macros.hpp>

#include "sum.h"

TEST_CASE("Simple") {
    CHECK(Sum(2, 3) == 5);
    CHECK(Sum(15, -16) == -1);
}
