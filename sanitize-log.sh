#! /bin/bash

cat "$1" | sed 's/^\[[0-9,.smh]*\]//g' | sed 's/0x[0-9a-f]*/0x????/g'
 

