"""Add @rule methods with bounded strategies derived from selected Vyper functions.

Use self.diagnostics.action(name, inputs={...}) around calls AND postconditions.
Use self.diagnostics.check("SP-01", assertion_callable) for stable property IDs.
Supply a separate rule with expected_revert=(SpecificContractError,) for an
intentional reverting case. Put ghost updates after a successful contract call.
Record actors by address and byte values directly; never record live contracts.
"""


class Actions:
    # Agent must implement selected valid flows, boundary and unauthorized cases.
    pass
