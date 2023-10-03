include(${CMAKE_CURRENT_SOURCE_DIR}/../tools/cmake/Guard.cmake)

add_catch_test(test_00_test sum.cpp test.cpp .private_test.cpp)
