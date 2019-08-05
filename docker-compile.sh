#!/bin/bash

docker run --rm \
  -v $(pwd):/compile \
  -u $(id -u):$(id -g) \
  -e "STATIC_CONTENT_HOST=.." \
  apluslms/compile-rst:1.6 \
  make touchrst html
