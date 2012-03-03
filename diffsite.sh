#!/bin/sh

site=$1
site=$( echo "${site}" | sed 's/.zip$// ; s/-BENCHMARK$//' )
zipsite="${site}.zip"
if [ ! -r ${zipsite} ] ; then
	echo "${zipsite} not found"
	exit 1
fi
rm -rf /tmp/${site}
mkdir /tmp/${site}
mkdir /tmp/${site}/BENCHMARK
mkdir /tmp/${site}/LATEST
unzip -q -d /tmp/${site}/BENCHMARK ${site}-BENCHMARK.zip
unzip -q -d /tmp/${site}/LATEST ${site}.zip
diff -r /tmp/${site}/BENCHMARK /tmp/${site}/LATEST

# cust for drupal
#diff -r /tmp/${site}/BENCHMARK /tmp/${site}/LATEST #
#	| egrep -v "form-|<script|<link"
rm -rf /tmp/${site}
