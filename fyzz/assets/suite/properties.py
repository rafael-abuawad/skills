"""Add @invariant methods, each with a docstring marker such as 'fyzz: GL-01'.

Use self.diagnostics.check("GL-01", assertion_callable) to retain failure IDs.
SP assertions use matching 'fyzz: SP-01' docstrings and are called by actions.
An invariant must compare meaningful independent state; do not add tautologies.
"""


class Properties:
    pass
