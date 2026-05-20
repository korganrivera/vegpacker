CC ?= gcc
CFLAGS ?= -O3 -std=c99 -Wall -Wextra
LDFLAGS ?= -lm

TARGET := vp
DEBUG_TARGET := vp_dbg
SRC := vp.c

.PHONY: all debug run clean

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) $(SRC) -o $(TARGET) $(LDFLAGS)

debug: CFLAGS := -O0 -g -std=c99 -Wall -Wextra
debug: $(DEBUG_TARGET)

$(DEBUG_TARGET): $(SRC)
	$(CC) $(CFLAGS) $(SRC) -o $(DEBUG_TARGET) $(LDFLAGS)

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET) $(DEBUG_TARGET)
