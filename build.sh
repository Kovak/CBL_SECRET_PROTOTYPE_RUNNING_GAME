currentdir=`pwd`
rm RunningGame-0.2-debug.apk
pushd ~/libraries/python-for-android/dist/default/
rm -rf ./bin/*
./build.py --package org.test.runninggame --name "Running Game" --version 0.2 --dir "$currentdir" debug
popd
cp ~/libraries/python-for-android/dist/default/bin/RunningGame-0.2-debug.apk ./