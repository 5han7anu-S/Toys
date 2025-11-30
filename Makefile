# OS: macOS / Linux (Only tested on Debian based distros)
# Prerequisites: g++ (C++17), OpenSSL Dev Libs

TARGET = find_dupes
SRC = cleanup.cc
COMPILER = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O3

# Check if brew exists (macOS) and find the correct OpenSSL path.
# If on Linux, this command will fail.
OPENSSL_PREFIX := $(shell brew --prefix openssl@3 2>/dev/null)

# If OPENSSL_PREFIX is empty, these paths are ignored,
# and the compiler relies on default system locations.
ifeq ($(OPENSSL_PREFIX),)
    # Fallback for Linux: rely on system paths
    LINK_PATHS =
    INCLUDE_PATHS =
else
    # macOS and Homebrew: Explicitly add Homebrew paths
    LINK_PATHS = -L$(OPENSSL_PREFIX)/lib
    INCLUDE_PATHS = -I$(OPENSSL_PREFIX)/include
endif

CPPFLAGS = $(CXXFLAGS)

# Libraries required: SSL/Crypto (OpenSSL) and Threading (C++17 required)
LDLIBS = -lssl -lcrypto -pthread
INSTALL_CMD_MACOS = "brew install openssl@3"
INSTALL_CMD_LINUX = "sudo apt-get update && sudo apt-get install libssl-dev"

.PHONY: all clean install-deps

all: $(TARGET)

$(TARGET): $(SRC)
	$(COMPILER) $(CPPFLAGS) $(INCLUDE_PATHS) $(SRC) -o $(TARGET) $(LINK_PATHS) $(LDLIBS)

clean:
	@echo "Cleaning up build artifacts..."
	rm -f $(TARGET)

install-deps:
	@echo "--------------------------------------------------------"
	@echo "To ensure OpenSSL is installed, run ONE of the following:"
	@echo "--------------------------------------------------------"
	@echo "If you are on macOS (with Homebrew):"
	@echo "  $(INSTALL_CMD_MACOS)"
	@echo ""
	@echo "If you are on Debian/Ubuntu:"
	@echo "  $(INSTALL_CMD_LINUX)"
	@echo "--------------------------------------------------------"

config:
	@echo "Compiler: $(COMPILER)"
	@echo "OpenSSL Prefix: $(OPENSSL_PREFIX)"
	@echo "Include Paths: $(INCLUDE_PATHS)"
	@echo "Linker Paths: $(LINK_PATHS)"
	@echo "Libraries: $(LDLIBS)"
