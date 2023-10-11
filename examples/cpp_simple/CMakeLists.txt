cmake_minimum_required(VERSION 3.14)

project(cpp-simple)

include(tools/cmake/BuildFlags.cmake)
include(tools/cmake/Test.cmake)

function(add_task name)
  if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${name})
    add_subdirectory(${name})
  endif()
endfunction()

add_task(00_test)
