#!/usr/bin/env bash

#P:cron:10 10,12,15,17 * * *
#P:cron:59 23 * * *
#T:cron:*/10 * * * *

cd $(dirname $0)

. functions.shl


