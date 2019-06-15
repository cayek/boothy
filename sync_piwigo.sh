#!/bin/sh

if nc -z -w5 photo.caye.fr 443
then
    timeout 10 scp $1  photo:/mnt/docker/piwigo/config/www/gallery/galleries/mariage/photomaton/
    timeout 10 ssh photo /home/piwigo/sync_piwigo.sh
    exit 0
else
    exit 1
fi


