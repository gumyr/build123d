import inspect
import enum
import sys
import os
from pygments.lexers.python import PythonLexer
from pygments.token import Name
from sphinx.highlighting import lexers

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
import build123d


class Build123dLexer(PythonLexer):
    """
    Python lexer extended with Build123d-specific highlighting.
    Dynamically pulls symbols from build123d.__all__.
    """

    EXTRA_SYMBOLS = set(getattr(build123d, "__all__", []))

    EXTRA_CLASSES = {
        n for n in EXTRA_SYMBOLS
        if n[0].isupper()
    }

    EXTRA_CONSTANTS = {
        n for n in EXTRA_SYMBOLS
        if n.isupper() and not callable(getattr(build123d, n, None))
    }

    EXTRA_ENUMS = {
        n for n in EXTRA_SYMBOLS
        if inspect.isclass(getattr(build123d, n, None)) and issubclass(getattr(build123d, n), enum.Enum)
    }

    EXTRA_FUNCTIONS = EXTRA_SYMBOLS - EXTRA_CLASSES - EXTRA_CONSTANTS - EXTRA_ENUMS

    def get_tokens_unprocessed(self, text):
        """
        Yield tokens, highlighting Build123d symbols, including chained accesses.
        """

        dot_chain = False
        for index, token, value in super().get_tokens_unprocessed(text):
            if value == ".":
                dot_chain = True
                yield index, token, value
                continue

            if dot_chain:
                # In a chain, don't use top-level categories
                if value[0].isupper():
                    yield index, Name.Class, value
                elif value.isupper():
                    yield index, Name.Constant, value
                else:
                    yield index, Name.Function, value
                dot_chain = False
                continue

            # Top-level classification from __all__
            if value in self.EXTRA_CLASSES:
                yield index, Name.Class, value
            elif value in self.EXTRA_FUNCTIONS:
                yield index, Name.Function, value
            elif value in self.EXTRA_CONSTANTS:
                yield index, Name.Constant, value
            elif value in self.EXTRA_ENUMS:
                yield index, Name.Builtin, value
            else:
                yield index, token, value

def setup(app):
    lexers["build123d"] = Build123dLexer()
    return {"version": "0.1"}