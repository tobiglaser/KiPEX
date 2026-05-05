#!/bin/bash

if [[ $# -eq 0 ]]
    then
        echo 'Specify Version e.g. "4.2.0"'
        exit
    else
        VERSION=$1
        STATUS="testing"
fi

echo ENV:
env

rm -rf build/*
mkdir -p build/plugins/icons

cp -rv resources/ build/
cp -v resources/icon.png build/plugins/icons/
cp -v src/icons/*.png build/plugins/icons/
cp -v src/*.py build/plugins/
cp -v src/requirements.txt build/plugins/requirements.txt
cp -v src/plugin.json build/plugins/plugin.json


jq  --arg version $VERSION \
    --arg status $STATUS \
    '(.versions[0]) += {"version": $version, "status": $status}' \
    metadata.json > build/metadata.json


FULLSIZE=($(du build/ -bcs))

cd build
zip KiPEX.zip -rv ./* 
cd -

ZIPSIZE=($(wc --bytes build/KiPEX.zip))
ZIPSHA=($(sha256sum build/KiPEX.zip))

if [[ $CI ]]
    then
        LINK="https://github.com/tobiglaser/KiPEX/releases/download/$VERSION/KiPEX.zip"
    else
        LINK="https://tobiglaser.de/kicad-tests/KiPEX.zip"
fi

jq  --argjson ds $ZIPSIZE \
    --argjson install $FULLSIZE \
    --arg sha $ZIPSHA \
    --arg url $LINK \
    --arg version $VERSION \
    --arg status $STATUS \
    '(.versions[0]) += {"version": $version, "status": $status, "download_size": $ds, "download_sha256": $sha, "install_size": $install, "download_url": $url}' \
    metadata.json > build/metadata.json

echo Metadata:
cat build/metadata.json
