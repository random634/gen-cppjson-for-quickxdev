## generate cppjson for QuickXDev


### why

the cpp.json in  ~/.vscode/extensions/lonewolf.vscode-quickxdev-0.1.0/files is too old


### how

* input a config file
* use libclang to generate

    ```
    Notice, when parse .h file:

    The libclang will take .h file as C language header file by default.

    We need pass a args '-xc++-header' or '-xc++', not '-x c++' for new version of libclang, so the libclang can parse it as C++ language.

    Refer from llvm-project/clang/unittests/libclang/LibclangTest.cpp.
    ```

* output the cpp.json

### depends

* python3
* libclang
  
  ```
  pip3 install libclang
  ```

### run

* prepare the env of COCOS_X_ROOT and NDK_ROOT
* config the generate.sh
* exec the generate.sh

### todos

* [x] parse the enums
* [ ] parse template type, like ParticlePool
* [ ] parse the function in namespace
* [ ] parse the field in class