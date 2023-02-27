DEBUG := 0

CXX := g++
CXXFLAGS := -O3 -Wall -std=c++17
LINKFLAGS := -lpcap

EXE := main
SRC := $(wildcard *.cpp)
OBJ := $(patsubst %.cpp, %.o, $(SRC))

ifeq ($(DEBUG), 1)
	CXXFLAGS += -DPRINT_DEVICES
endif

.PHONY: all clean

all: $(EXE)

$(EXE): $(OBJ)
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LINKFLAGS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) $^ -c -o $@

clean:
	-rm $(EXE)
	-rm $(OBJ)
