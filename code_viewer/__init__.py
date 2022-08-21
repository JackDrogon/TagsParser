# coding: utf-8

from .buffer import Buffer
from .symbol import Symbol
from .variable import Variable
from .klass import Class, ClassFunction
from .class_manager import ClassManager, NotFoundClassError
from .tag_manager import TagManger
from .tag_parser import TagParser
from .namespace import Namespace
from .plantumler import PlantUMLer
from . import utils


# TODO
class ProgrammgingLanguageManager():

    def __init__(self, name: str) -> None:
        self.name = name
