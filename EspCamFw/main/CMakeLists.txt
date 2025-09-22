set(CMAKE_C_COMPILER_LAUNCHER ccache)
set(CMAKE_CXX_COMPILER_LAUNCHER ccache)
set(CMAKE_EXPORT_COMPILE_COMMANDS TRUE)

idf_component_register(
  SRCS #
  #
  Main.c
  #
  INCLUDE_DIRS
  "." #
)

include(Secrets.cmake OPTIONAL)

if(WIFI_SSID AND WIFI_PASS)
  target_compile_definitions(
    ${COMPONENT_LIB}
    PRIVATE #
            WIFI_SSID="${WIFI_SSID}" #
            WIFI_PASS="${WIFI_PASS}" #
  )
endif()
