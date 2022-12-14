from configparser import ConfigParser
import json
from optparse import OptionParser
import os
import re
import sys
import traceback
import clang.cindex


class Generator(object):
    def __init__(
        self,
        target_namespace: str,
        headers: str,
        classes: str,
        abstract_classes: str,
        skip_info: str,
        rename_classes: str,
        rename_functions: str,
        cocosx_dir: str,
        ndk_dir: str,
    ) -> None:
        self.target_namespace = target_namespace
        self.headers = re.split("[ \t]+", headers)
        self.classes = re.split("[ \t]+", classes)
        self.abstract_classes = re.split("[ \t]+", abstract_classes)
        self.skip_info = {}
        self.rename_classes = {}
        self.rename_functions = {}
        self.cocosx_dir = cocosx_dir.removesuffix("/")
        self.ndk_dir = ndk_dir.removesuffix("/")

        self.json_data = {"name": self.target_namespace, "loc": None, "classes": []}

        if skip_info:
            list_of_skips = re.split(",\n?", skip_info)
            for skip in list_of_skips:
                class_name, methods = skip.split("::")
                self.skip_info[class_name] = []

                match = re.match("\[([^]]+)\]", methods)
                if match:
                    self.skip_info[class_name] = re.split("[ \t]+", match.group(1))
                else:
                    raise Exception("invalid list of skip methods")

        if rename_classes:
            list_of_class_renames = re.split(",\n?", rename_classes)
            for rename in list_of_class_renames:
                class_name, renamed_class_name = rename.split("::")
                self.rename_classes[class_name] = renamed_class_name

        if rename_functions:
            list_of_function_renames = re.split(",\n?", rename_functions)
            for rename in list_of_function_renames:
                class_name, methods = rename.split("::")
                self.rename_functions[class_name] = {}
                match = re.match("\[([^]]+)\]", methods)
                if match:
                    list_of_methods = re.split("[ \t]+", match.group(1))
                    for pair in list_of_methods:
                        k, v = pair.split("=")
                        self.rename_functions[class_name][k] = v
                else:
                    raise Exception("invalid list of rename methods")

    def get_class_name_reg(self, class_name: str) -> str:
        if class_name in self.rename_classes:
            return self.rename_classes[class_name]

        return class_name

    def get_method_name_reg(self, class_name: str, method_name: str) -> str:
        if (
            class_name in self.rename_functions
            and method_name in self.rename_functions[class_name]
        ):
            return self.rename_functions[class_name][method_name]

        return method_name

    def get_json_data(self) -> dict:
        return self.json_data

    def parse_header(self, verbose: bool = False):
        index: clang.cindex.Index = clang.cindex.Index.create()

        for header in self.headers:
            translation_unit = index.parse(
                header,
                args=[
                    "-xc++",
                    "-nostdinc",
                    "-std=c++11",
                    "-fsigned-char",
                    "-U__SSE__",
                    "-I%s/cocos" % self.cocosx_dir,
                    "-I%s/external" % self.cocosx_dir,
                    "-I%s/cocos/editor-support" % self.cocosx_dir,
                    "-U__APPLE__",
                    "-DANDROID",
                    "-I%s/cocos/platform/android" % self.cocosx_dir,
                    "-I%s/sysroot/usr/include" % self.ndk_dir,
                    "-I%s/sysroot/usr/include/arm-linux-androideabi" % self.ndk_dir,
                    "-I%s/sources/android/support/include" % self.ndk_dir,
                    "-I%s/sources/cxx-stl/llvm-libc++/include" % self.ndk_dir,
                    "-I%s/toolchains/llvm/prebuilt/darwin-x86_64/lib64/clang/9.0.9/include"
                    % self.ndk_dir,
                ],
            )

            # if len(translation_unit.diagnostics) > 0:
            #     for i in translation_unit.diagnostics:
            #         print(i)

            self.parse_node(translation_unit.cursor, verbose=verbose)

    def parse_node(
        self, node: clang.cindex.Cursor, parents: list = [], verbose: bool = False
    ):
        if node.kind == clang.cindex.CursorKind.CLASS_DECL:
            if self.in_listed_classes(node.displayname):
                self.parse_class(node, parents, verbose)
        elif (
            node.kind == clang.cindex.CursorKind.TRANSLATION_UNIT
            or node.kind == clang.cindex.CursorKind.NAMESPACE
        ):
            parents.append(node)
            for child in node.get_children():
                self.parse_node(child, parents, verbose)
            parents.pop()

    def parse_class(self, node: clang.cindex.Cursor, parents: list, verbose: bool):
        class_name = node.displayname
        class_name_reg = self.get_class_name_reg(class_name)
        class_is_abstract = class_name in self.abstract_classes

        class_info = None
        class_has_new = False
        class_need_add = True
        for clazz in self.json_data["classes"]:
            if clazz["name"] == class_name_reg:
                class_info = clazz
                class_need_add = False

        child: clang.cindex.Cursor = None
        for child in node.get_children():
            if not class_info:
                location = node.location
                src = location.file
                line = location.line
                char = location.column

                class_info = {
                    "name": class_name_reg,
                    "loc": {
                        "src": str(src).replace(self.cocosx_dir + "/", ""),
                        "line": line,
                        "char": char,
                    },
                    "functions": [],
                }

            if child.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER:
                pass
            elif child.kind == clang.cindex.CursorKind.FIELD_DECL:
                pass
            elif child.kind == clang.cindex.CursorKind.CXX_ACCESS_SPEC_DECL:
                pass
            elif child.kind == clang.cindex.CursorKind.CONSTRUCTOR:
                if (
                    class_is_abstract
                    or class_has_new
                    or child.access_specifier != clang.cindex.AccessSpecifier.PUBLIC
                ):
                    continue

                class_has_new = True
                method_name_reg = "new"

                location = child.location
                src = location.file
                line = location.line
                char = location.column

                function_info = {
                    "name": method_name_reg,
                    "params": [],
                    "loc": {
                        "src": str(src).replace(self.cocosx_dir + "/", ""),
                        "line": line,
                        "char": char,
                    },
                }

                class_info["functions"].append(function_info)

                if verbose:
                    print(class_name, method_name_reg, params, src, line, char)
            elif child.kind == clang.cindex.CursorKind.CXX_METHOD:
                if child.access_specifier == clang.cindex.AccessSpecifier.PUBLIC:
                    method_name = child.spelling
                    if self.should_skip(class_name, method_name, verbose):
                        continue

                    method_name_reg = self.get_method_name_reg(class_name, method_name)

                    params = []
                    for arg in child.get_arguments():
                        params.append(arg.spelling)

                    location = child.location
                    src = location.file
                    line = location.line
                    char = location.column

                    function_info = {
                        "name": method_name_reg,
                        "params": params,
                        "loc": {
                            "src": str(src).replace(self.cocosx_dir + "/", ""),
                            "line": line,
                            "char": char,
                        },
                    }

                    class_info["functions"].append(function_info)

                    if verbose:
                        print(class_name, method_name, params, src, line, char)

        if class_need_add and class_info:
            self.json_data["classes"].append(class_info)

    def in_listed_classes(self, class_name: str) -> bool:
        for key in self.classes:
            md = re.match("^" + key + "$", class_name)
            if md:
                return True
        return False

    def should_skip(
        self, class_name: str, method_name: str, verbose: bool = False
    ) -> bool:
        for key in self.skip_info:
            if key == "*" or re.match("^" + key + "$", class_name):
                if len(self.skip_info[key]) == 1 and self.skip_info[key][0] == "*":
                    if verbose:
                        print("%s will be skipped completely" % class_name)
                    return True
                if method_name != None:
                    for func in self.skip_info[key]:
                        if re.match(func, method_name):
                            if verbose:
                                print(
                                    "%s %s will be skipped" % (class_name, method_name)
                                )
                            return True
        if verbose:
            print("%s %s will be accepted" % (class_name, method_name))
        return False


def main():
    # working_dir = os.path.abspath(os.path.curdir)
    # print("Working directoy: ", working_dir)

    COCOS_X_ROOT = os.environ["COCOS_X_ROOT"]
    NDK_ROOT = os.environ["NDK_ROOT"]

    parser = OptionParser("usage: %prog [options] {configfile} {outputfile}")
    parser.add_option(
        "-s",
        action="store",
        type="string",
        dest="section",
        help="sets a specific section to be converted",
    )

    (opts, args) = parser.parse_args()
    if len(args) <= 1:
        parser.error("invalid number of arguments")

    config = ConfigParser()
    config.read(args[0])

    sections = []
    if opts.section:
        if opts.section in config.sections():
            sections.append(opts.section)
        else:
            raise Exception("Section %s not found in config file" % opts.section)
    else:
        sections = config.sections()

    default_dict = {"cocosdir": COCOS_X_ROOT, "androidndkdir": NDK_ROOT}

    json_ret = {}
    for s in sections:
        # print("processing section %s" % s)
        target_namespace = config.get(s, "target_namespace", vars=default_dict)
        headers = config.get(s, "headers", vars=default_dict)
        classes = config.get(s, "classes", vars=default_dict)
        abstract_classes = config.get(s, "abstract_classes", vars=default_dict)
        skip = config.get(s, "skip", vars=default_dict)
        rename_classes = config.get(s, "rename_classes", vars=default_dict)
        rename_functions = config.get(s, "rename_functions", vars=default_dict)

        generator = Generator(
            target_namespace,
            headers,
            classes,
            abstract_classes,
            skip,
            rename_classes,
            rename_functions,
            COCOS_X_ROOT,
            NDK_ROOT,
        )
        generator.parse_header()
        json_data = generator.get_json_data()
        json_ret.update(json_data)

    if json_ret["name"]:
        json_all = []
        if os.path.exists(args[1]):
            fi = open(args[1], "r")
            json_str = fi.read()
            json_all = json.loads(json_str)
            fi.close()

        has_updated = False
        for namespace_obj in json_all:
            if namespace_obj["name"] and namespace_obj["name"] == json_ret["name"]:
                namespace_obj.update(json_ret)
                has_updated = True
                break
        if not has_updated:
            json_all.append(json_ret)

        fo = open(args[1], "w+")
        fo.write(json.dumps(json_all, indent=2))
        fo.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
