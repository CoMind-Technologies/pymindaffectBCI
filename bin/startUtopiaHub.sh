#!/bin/bash
cd `dirname ${BASH_SOURCE[0]}`
uid=`date +%y%m%d_%H%M`

mkdir ../logs

# start up the utopia-hub
echo Starting the Utopia-HUB
if [ ! -z `which xterm`]; then
    # start in new xterm
    xterm -iconic -title "Utopia-HUB" java -jar UtopiaServer.jar 8400 0 ../logs/mindaffectBCI.txt
else # run directly
   java -jar UtopiaServer.jar 8400 0 ../logs/mindaffectBCI.txt 
fi
