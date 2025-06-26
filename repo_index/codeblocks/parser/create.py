from typing import Optional

from repo_index.codeblocks import JavaParser
from repo_index.codeblocks.parser.go import GoParser
from repo_index.codeblocks.parser.parser import CodeParser
from repo_index.codeblocks.parser.python import PythonParser

LANGUAGE_TYPE_PYTHON = 'python'
LANGUAGE_TYPE_JAVA = 'java'
LANGUAGE_TYPE_TS = 'typescript'
LANGUAGE_TYPE_JS = 'javascript'
LANGUAGE_TYPE_GO = 'go'

VALID_LANGUAGE_TYPES = [LANGUAGE_TYPE_PYTHON, LANGUAGE_TYPE_JAVA, LANGUAGE_TYPE_TS, LANGUAGE_TYPE_JS, LANGUAGE_TYPE_GO]


def is_supported(language: str) -> bool:
    return language in VALID_LANGUAGE_TYPES


def create_parser(language: str, **kwargs) -> Optional[CodeParser]:
    if language == LANGUAGE_TYPE_PYTHON:
        return PythonParser(**kwargs)
    elif language == LANGUAGE_TYPE_JAVA:
        return JavaParser(**kwargs)
    elif language == LANGUAGE_TYPE_GO:
        return GoParser(**kwargs)

    raise NotImplementedError(f'Language {language} is not supported.')
