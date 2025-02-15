#!/bin/bash
while :
do
	echo "=========================="
	echo ""
	FETCH=`(time time wget -O snapshot.jpg http://admin:salek2025@192.168.1.115/cgi-bin/snapshot.cgi -q) 2>&1`
	DECODE=`(time dmtxread snapshot.jpg -n -N 8 -s 22x22  -q 5 -t 40 -e 95 -E 125 -m 1000 | wc -l) 2>&1`
	echo "FETCHING"
	echo "${FETCH}"
	echo ""
	echo "DECODING"
	echo "${DECODE}"
done
