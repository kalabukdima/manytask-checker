Include(FetchContent)

FetchContent_Declare(
  Catch2
  GIT_REPOSITORY https://github.com/catchorg/Catch2.git
  GIT_TAG        v3.4.0
)
FetchContent_MakeAvailable(Catch2)

function(filter_existing OUT_VAR)
  foreach(_file ${ARGN})
    if (EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${_file})
      list(APPEND RESULT ${_file})
    endif()
  endforeach()
  set(${OUT_VAR} ${RESULT} PARENT_SCOPE)
endfunction()

function(add_catch_test TARGET)
  filter_existing(SRCS ${ARGN})
  add_executable(${TARGET} ${SRCS})
  target_link_libraries(${TARGET} PRIVATE Catch2::Catch2WithMain)
endfunction()
