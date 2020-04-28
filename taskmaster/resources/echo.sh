#!/bin/sh

echo "echoing to stdout"
>&2 echo "echoing to stderr"
sleep 5
exit 0