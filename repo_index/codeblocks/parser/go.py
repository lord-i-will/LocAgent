from tree_sitter_languages import get_language

from repo_index.codeblocks import CodeParser


class GoParser(CodeParser):
    def __init__(self, **kwargs):
        language = get_language('go')

        super().__init__(language, **kwargs)
        self.queries.extend(self._build_queries('go.scm'))

    @property
    def language(self):
        return 'go'
