#!/usr/bin/env bash

TARGET="109652039_hw1.zip"

zip ${TARGET} -j src/*.{cpp,hpp}
zip ${TARGET} -j src/Makefile
zip ${TARGET} -j report.pdf
printf "@ report.pdf\n@=109652039_hw1.pdf\n" | zipnote -w ${TARGET}
