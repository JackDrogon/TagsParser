#!/usr/bin/env python3

import sys
import json

# {"_type"=>"tag",
#  "name"=>"AcceptAndReply",
#  "path"=>"raft/raft_paper_test.cc",
#  "pattern"=>
#   "/^  static std::unique_ptr<Message> AcceptAndReply(std::unique_ptr<Message> msg) {$/",
#  "file"=>true,
#  "typeref"=>"typename:std::unique_ptr<Message>",
#  "kind"=>"function",
#  "scope"=>"byteraft::ConsensusTest",
#  "scopeKind"=>"class"}


class Symbol():

    def __init__(self, tag) -> None:
        self.name = tag['name']
        # FIXME
        self.filename = tag.get('path', "")
        self.line = 0
        self.body = ""

    def __str__(self) -> str:
        return f"{self.name} {self.filename}:{self.line}"

    def __repr__(self) -> str:
        return self.__str__()


# maybe to all function
class ClassFunction(Symbol):

    def __init__(self, tag) -> None:
        super().__init__(tag)


class Variable(Symbol):

    def __init__(self, tag) -> None:
        super().__init__(tag)


def remove_anon(name: str) -> str:
    # if scope split by ::, any one contains str startwiths "__anon", remove it
    # like leveldb::__anon2cdfda410111::PosixEnv => leveldb::PosixEnv
    for field in name.split("::"):
        if field.startswith("__anon"):
            name = name.replace(f"{field}::", "")
    return name


class Class(Symbol):
    """
    scope = "", class is in global namespace
    """

    def __init__(self, tag) -> None:
        super().__init__(tag)
        self.scope = tag.get('scope', "")
        self.variables = []
        self.functions = []
        self.is_anon = False
        self.__maybe_fix_name()

    """fix the name of class"""

    def __maybe_fix_name(self):
        # if name not start with scope name, add scope name to the front
        # like DataFile leveldb::SpecialEnv::NewWritableFile => leveldb::SpecialEnv::NewWritableFile::Data
        if not self.name.startswith(self.scope):
            self.name = self.scope + "::" + self.name

        name = remove_anon(self.name)
        if name != self.name:
            self.is_anon = True
            self.name = name

    def __str__(self) -> str:
        # FIXME
        return f"class: {self.name}\nmembers: {self.variables}\nfunctions: {self.functions}"

    def add_function(self, tag: dict) -> None:
        self.functions.append(ClassFunction(tag))

    def add_variable(self, tag: dict) -> None:
        self.variables.append(Variable(tag))


class Namespace():
    pass


class ClassManger():

    def __init__(self) -> None:
        self.classes = {}

    def __lshift__(self, tag: dict) -> Class:
        klass = Class(tag)
        self.classes[klass.name] = klass

    def __add_function(self, class_name: str, tag: dict) -> bool:
        if class_name in self.classes:
            self.classes[class_name].add_function(tag)
            return True
        return False

    """
    function: add function tag, delegate to class
    """

    def add_function(self, tag: dict) -> None:
        raw_class_name = tag['scope']
        if self.__add_function(raw_class_name, tag):
            return

        # FIXME: need to check scope is anon class
        # check tag is in cpp impl file not header
        class_name = remove_anon(raw_class_name)
        if self.__add_function(class_name, tag):
            return

        raise NotFoundClassError(raw_class_name)

    def __add_variable(self, class_name: str, tag: dict) -> bool:
        if class_name in self.classes:
            self.classes[class_name].add_variable(tag)
            return True
        return False

    """
    function: add variable tag, delegate to class
    """

    def add_variable(self, tag: dict) -> None:
        raw_class_name = tag['scope']
        if self.__add_variable(raw_class_name, tag):
            return

        # FIXME: need to check scope is anon class
        # check tag is in cpp impl file not header
        class_name = remove_anon(raw_class_name)
        if self.__add_variable(class_name, tag):
            return

        raise NotFoundClassError(raw_class_name)


class TagManger():

    def __init__(self) -> None:
        self.tags = {}
        self.class_manager = ClassManger()
        self.function_manger = {}
        self.variable_manger = {}

    def __lshift__(self, tag) -> None:
        self.tags[tag['name']] = tag
        # kind is class, add to class manager
        kind = tag.get('kind', '')

        if kind == '':
            return
        elif kind == 'class' or kind == 'struct':
            self.class_manager << tag
        # kind is function, add to function manager
        elif kind == 'function':
            self.add_function(tag)
        # kind is variable, add to variable manager
        elif kind == 'variable':
            self.add_variable(tag)
        elif kind == 'member':
            self.add_member(tag)

    """
    add function tag

    if function scopeKind is class, call class_manager add function tag
    """

    def add_function(self, tag: dict) -> None:
        scope_kind = tag.get('scopeKind', '')
        if scope_kind == 'class' or scope_kind == 'struct':
            self.class_manager.add_function(tag)
        else:
            self.function_manger[tag['name']] = tag

    """
    add variable tag

    if function scopeKind is class, call class_manager add variable tag
    """

    def add_variable(self, tag: dict):
        scope_kind = tag.get('scopeKind', '')
        if scope_kind == 'class' or scope_kind == 'struct':
            self.class_manager.add_variable(tag)
        else:
            self.variable_manger[tag['name']] = tag

    def add_member(self, tag: dict):
        self.class_manager.add_variable(tag)


# def show_class(filename: str):
#     file = open(filename, 'r')
#     for line in file:
#         entry = json.loads(line)
#         # print(data['class'])
#         if "kind" in entry and entry['kind'] == 'class':
#             print(entry['name'])


# TODO
class ProgrammgingLanguageManager():

    def __init__(self, name: str) -> None:
        self.name = name


class NotFoundClassError(Exception):

    def __init__(self, message: str) -> None:
        self.message = message


class TagParser():

    def __init__(self, tags_filename: str):
        self.tags_filename = tags_filename

    def add_tags(self, tag_manager: TagManger) -> None:
        # first pass
        second_pass_tags = []
        file = open(self.tags_filename, 'r')
        for line in file:
            tag = json.loads(line)
            if tag.get('language', '') != 'C++':
                continue
            try:
                tag_manager << tag
            except NotFoundClassError:
                second_pass_tags.append(tag)

        # second pass, handle class not found in first pass
        # print("send second pass")
        for tag in second_pass_tags:
            tag_manager << tag


def main():
    tag_parser = TagParser(sys.argv[1])
    tag_manager = TagManger()
    tag_parser.add_tags(tag_manager)
    # print(tag_manager.class_manager.classes)
    for klass in tag_manager.class_manager.classes.values():
        print(klass.name, klass.scope)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
