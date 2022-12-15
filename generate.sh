#!/bin/bash

# export COCOS_X_ROOT=''
# export NDK_ROOT=''

PYTHON_BIN=python3
OUTPUT_FILE=config.out/cpp.json

CONFIG_FILES=(
    config.in/cocos2dx.ini
    config.in/cocos2dx_studio.ini
    config.in/cocos2dx_video.ini
    config.in/cocos2dx_extension.ini
    config.in/cocos2dx_controller.ini
    config.in/cocos2dx_physics3d.ini
    config.in/cocos2dx_csloader.ini
    config.in/cocos2dx_ui.ini
    config.in/cocos2dx_webview.ini
    config.in/cocos2dx_3d.ini
    config.in/cocos2dx_physics.ini
    config.in/cocos2dx_spine.ini
    config.in/cocos2dx_navmesh.ini
    config.in/cocos2dx_backend.ini
    config.in/ext_fairygui.ini

    # config.in/cocos2dx_audioengine.ini
)


echo rm -f $OUTPUT_FILE
rm -f $OUTPUT_FILE

for config in ${CONFIG_FILES[@]}; do
    echo $PYTHON_BIN src/generator.py $config $OUTPUT_FILE
    $PYTHON_BIN src/generator.py $config $OUTPUT_FILE
done
