#!/bin/bash
while :
do
	echo ""
	echo "=========================="
	echo "FETCHING"
	time wget -O snapshot.jpg http://admin:salek2025@192.168.1.115/cgi-bin/snapshot.cgi -q
	echo "DECODING"
	time dmtxread snapshot.jpg -n -N 8 -s 22x22  -q 5 -t 40 -e 95 -E 125 -m 1000 | wc -l
done
