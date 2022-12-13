from configparser import ConfigParser
from optparse import OptionParser
import os
import re
import sys
import traceback
import typing
import clang.cindex


def is_exposed_field(node: clang.cindex.Cursor):
    return node.access_specifier == clang.cindex.AccessSpecifier.PUBLIC


def filter_node_list_by_file(
    nodes: typing.Iterable[clang.cindex.Cursor], file_name: str
) -> typing.Iterable[clang.cindex.Cursor]:
    result = []
    for i in nodes:
        if i.location.file.name == file_name:
            result.append(i)
    return result


def filter_node_list_by_node_kind(
    nodes: typing.Iterable[clang.cindex.Cursor], kinds: list
) -> typing.Iterable[clang.cindex.Cursor]:
    result = []
    for i in nodes:
        if i.kind in kinds:
            result.append(i)
    return result


def find_all_exposed_fields(
    cursor: clang.cindex.Cursor,
) -> typing.Iterable[clang.cindex.Cursor]:
    result = []
    field_declarations = filter_node_list_by_node_kind(
        cursor.get_children(), [clang.cindex.CursorKind.FIELD_DECL]
    )
    for i in field_declarations:
        if not is_exposed_field(i):
            continue
        result.append(i.displayname)
    return result


class Generator(object):
    def __init__(
        self, target_namespace: str, headers: str, classes: str, skip_info: str
    ) -> None:
        self.target_namespace = target_namespace
        self.headers = re.split("[ \t]+", headers)
        self.classes = re.split("[ \t]+", classes)
        self.skip_info = {}

        list_of_skips = re.split(",\n?", skip_info)
        for skip in list_of_skips:
            class_name, methods = skip.split("::")
            self.skip_info[class_name] = []

            match = re.match("\[([^]]+)\]", methods)
            if match:
                self.skip_info[class_name] = re.split("[ \t]+", match.group(1))
            else:
                raise Exception("invalid list of skip methods")

    def parse_header(self):
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
                    "-I/Applications/Cocos/Cocos2d-Lua-Community/cocos",
                    "-I/Applications/Cocos/Cocos2d-Lua-Community/external",
                    "-I/Applications/Cocos/Cocos2d-Lua-Community/cocos/editor-support",
                    "-D__APPLE__",
                    "-I/Applications/Cocos/Cocos2d-Lua-Community/cocos/platform/apple",
                    "-I/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include",
                    "-I/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/include",
                    "-I/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/include/c++/v1",
                    "-I/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/14.0.0/include"
                ],
            )

            if len(translation_unit.diagnostics) > 0:
                for i in translation_unit.diagnostics:
                    print(i)
            print("---------")
            self.parse_node(translation_unit.cursor)
    
    def parse_node(self, node: clang.cindex.Cursor):
        if node.kind == clang.cindex.CursorKind.CLASS_DECL and self.in_listed_classes(node.displayname):
            print(node.displayname)
            print(node.location)
        
        for child in node.get_children():
            self.parse_node(child)

    def in_listed_classes(self, class_name: str) -> bool:
        """
        returns True if the class is in the list of required classes
        """
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
                if verbose:
                    print("%s in skip_info" % (class_name))
                if len(self.skip_info[key]) == 1 and self.skip_info[key][0] == "*":
                    if verbose:
                        print("%s will be skipped completely" % (class_name))
                    return True
                if method_name != None:
                    for func in self.skip_info[key]:
                        if re.match(func, method_name):
                            if verbose:
                                print(
                                    "%s will skip method %s" % (class_name, method_name)
                                )
                            return True
        if verbose:
            print("(%s:%s) will be accepted" % (class_name, method_name))
        return False


def main():
    working_dir = os.path.abspath(os.path.curdir)
    print("Working directoy: ", working_dir)

    COCOS_X_ROOT = os.environ["COCOS_X_ROOT"]
    NDK_ROOT = os.environ["NDK_ROOT"]

    parser = OptionParser("usage: %prog [options] {configfile}")
    parser.add_option(
        "-s",
        action="store",
        type="string",
        dest="section",
        help="sets a specific section to be converted",
    )

    (opts, args) = parser.parse_args()
    if len(args) == 0:
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
        print("processing all sections")
        sections = config.sections()

    default_dict = {"cocosdir": COCOS_X_ROOT, "androidndkdir": NDK_ROOT}

    for s in sections:
        target_namespace = config.get(s, "target_namespace", vars=default_dict)
        headers = config.get(s, "headers", vars=default_dict)
        classes = config.get(s, "classes", vars=default_dict)
        skip = config.get(s, "skip", vars=default_dict)

        print("---------")
        print(target_namespace)
        print("---------")
        print(headers)
        print("---------")
        print(classes)
        print("---------")
        print(skip)
        generator = Generator(target_namespace, headers, classes, skip)
        generator.parse_header()
    return

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
