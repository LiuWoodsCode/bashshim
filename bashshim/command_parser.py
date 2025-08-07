import os
import re
import shlex
from typing import List, Tuple, Optional

class CommandParser:
    """Helper responsible for basic bash-like command parsing & variable expansion.

    This keeps parsing logic out of the core BashShim implementation so that
    the shell implementation can focus on command dispatch & simulation.
    """

    def __init__(self, variables: dict, env: Optional[dict] = None):
        # We keep a reference to the shared variables dict (not a copy) so
        # assignments in BashShim remain visible here automatically.
        self.variables = variables
        self.env = env if env is not None else os.environ

    # -------------------- Variable expansion --------------------
    _VAR_PATTERN = re.compile(r'\$(\w+)|\$\{([^}]+)\}')

    def expand_vars(self, s: str) -> str:
        def repl(m):
            var = m.group(1) or m.group(2)
            return self.variables.get(var, self.env.get(var, ''))
        return self._VAR_PATTERN.sub(repl, s)

    def expand_args(self, args: List[str]) -> List[str]:
        return [self.expand_vars(a) for a in args]

    # -------------------- Redirection parsing --------------------
    def parse_redirection(self, cmd: str) -> Tuple[List[str], Optional[str], bool]:
        """Parse a single (non‑piped) command for simple output redirection.

        Returns (tokens_without_redir, out_file, append_flag)
        """
        tokens = shlex.split(cmd)
        tokens = self.expand_args(tokens)
        if '>>' in tokens:
            idx = tokens.index('>>')
            return tokens[:idx], tokens[idx + 1] if idx + 1 < len(tokens) else None, True
        if '>' in tokens:
            idx = tokens.index('>')
            return tokens[:idx], tokens[idx + 1] if idx + 1 < len(tokens) else None, False
        return tokens, None, False

    # -------------------- Pipe splitting --------------------
    def split_pipes(self, command_line: str) -> List[str]:
        # NOTE: Current implementation is naive (does not honor escapes inside quotes)
        # to remain consistent with previous inline logic.
        return [c.strip() for c in command_line.split('|')]

    # -------------------- Shell operator splitting (; && ||) --------------------
    def split_shell_operators(self, cmdline: str) -> List[str]:
        tokens: List[str] = []
        buf = ''
        i = 0
        length = len(cmdline)
        while i < length:
            two = cmdline[i:i+2]
            if two == '&&' or two == '||':
                if buf.strip():
                    tokens.append(buf.strip())
                tokens.append(two)
                buf = ''
                i += 2
                continue
            ch = cmdline[i]
            if ch == ';':
                if buf.strip():
                    tokens.append(buf.strip())
                tokens.append(';')
                buf = ''
                i += 1
                continue
            buf += ch
            i += 1
        if buf.strip():
            tokens.append(buf.strip())
        return tokens

    def has_shell_operators(self, command_line: str) -> bool:
        return any(op in command_line for op in [';', '&&', '||'])
