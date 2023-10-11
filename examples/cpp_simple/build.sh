#!/bin/bash

ROOT_DIR=$(realpath $(dirname $0))

TARGET=$1
if [ -z $TARGET ]; then
    echo "usage: ./build.sh TARGET"
    exit 1
fi

BUILD_DIR=${BUILD_DIR-"$ROOT_DIR/build"}
echo BUILD_DIR=$BUILD_DIR


mkdir -p $BUILD_DIR
cmake -G Ninja -B "$BUILD_DIR" -S "$ROOT_DIR"
cmake --build "$BUILD_DIR" -t "$TARGET"
