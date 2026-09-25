# Vyper Best Practices — Reference

Detailed guidance for the [Vyper Best Practices skill](SKILL.md).

## Version and source selection

1. Read the contract's `#pragma version` and the project's compiler configuration before choosing syntax. Keep the existing target unless the user asks to change it.
2. Use the [Vyper development documentation](https://docs.vyperlang.org/en/latest/) for current patterns and upcoming features. It may describe features absent from released compilers, so confirm each feature against the target version's docs or compiler before using it.
3. Use the versioned [Vyper language documentation](https://docs.vyperlang.org/en/stable/) for released syntax and the [release notes](https://docs.vyperlang.org/en/latest/release-notes.html) to identify when features changed.
4. Use [Titanoboa documentation](https://titanoboa.readthedocs.io/en/latest/) for Boa-specific development and testing behavior. Use the [pcaversaccio Vyper list](https://github.com/stars/pcaversaccio/lists/vyper), the [Vyper resources page](https://docs.vyperlang.org/en/latest/resources.html), and [snekmate](https://github.com/pcaversaccio/snekmate) to discover tools and libraries. Check maintenance status, compiler compatibility, and dependency requirements before adopting a project; these lists do not define Vyper syntax.

When a compiler is available, run `vyper --version` and compile each complete example with that compiler. A passing compile confirms syntax compatibility, not security. If the target compiler is unavailable, use its versioned docs and identify the unverified constraint.

The complete examples below were compiled during this update with Vyper `0.5.0a4+commit.6b47556e`. They omit a version pragma so adopting projects can keep their own compiler target.

## Flags and constants

A `flag` is a typed set of named bits. Prefer it over hand-built integer constants when values represent roles, permissions, or options that may be combined. Use `in` for bit membership and `==` for exact equality of the entire value. A constant remains appropriate for one fixed value such as a maximum, address, selector, or domain separator.

This complete example uses Vyper flag and constant syntax:

```vyper
flag Capability:
    PAUSE
    WITHDRAW

MAX_BATCH: constant(uint256) = 64

@external
@view
def may_pause(available: Capability) -> bool:
    return Capability.PAUSE in available

@external
@view
def has_exact_capabilities(available: Capability) -> bool:
    return available == (Capability.PAUSE | Capability.WITHDRAW)
```

A `flag` can contain combined members, so equality and membership answer different questions. If a function requires exactly one option, compare to that member with `==`; if it only requires a capability, check membership with `in`.

## Revert reasons

Use an on-chain reason string when a user or integrator benefits from receiving an explanatory revert. Vyper also permits a bare `assert` or `raise`; strings add deployment bytecode and runtime cost.

For projects using Titanoboa, a `# dev: "..."` comment after an assertion lets Boa attach an off-chain developer reason when it can trace the source. It has no on-chain effect and Vyper ignores it as a comment. Tests can assert this reason with `boa.reverts(dev="...")`.

```vyper
@external
def check_amount(amount: uint256, limit: uint256):
    assert amount > 0  # dev: "amount must be positive"
    assert amount <= limit, "amount exceeds limit"

@external
def reject_unsupported_operation():
    raise "unsupported operation"
```

The dev comment is optional: add it where a clearer Titanoboa test failure is useful. Keep an on-chain reason string where callers need an on-chain message.

## External calls and deployment

Declare interface mutability and make the call kind explicit. This complete example uses `staticcall` for a read and `extcall` for a state-changing call:

```vyper
interface IToken:
    def balanceOf(account: address) -> uint256: view
    def transfer(to: address, amount: uint256) -> bool: nonpayable

@external
@view
def token_balance(token: IToken, account: address) -> uint256:
    return staticcall token.balanceOf(account)

@external
def transfer_token(token: IToken, to: address, amount: uint256):
    success: bool = extcall token.transfer(to, amount)
    assert success, "token: transfer failed"
```

Use `@payable` on an external function only when it is intended to receive ETH. For constructors, `@deploy` is required and `@payable` is appropriate only when deployment should accept ETH:

```vyper
OWNER: immutable(address)

@deploy
def __init__():
    OWNER = msg.sender
```

## Modules

Use `initializes:` when the contract initializes a module's state and calls its initializer. Use `uses:` when the contract accesses module state initialized elsewhere. Add `exports:` only when a module's external functions should become part of the contract interface. These are contextual declarations: check the imported module's interface and initializer before wiring it.

When one module depends on another, bind the dependency with Vyper's module parameter syntax, for example `initializes: erc721[ownable := ownable_module]`. This is an excerpt; the actual import aliases and module declarations must match the dependency.

## Security and API notes

- Review state changes around every external call. Protect entrypoints when a callback can observe or exploit temporarily inconsistent state; understand that `@nonreentrant` uses one global lock.
- The file pragma `#pragma nonreentrancy on` enables protection broadly for external functions and public getters in supported compiler versions. Check the selected version and intentional reentrant paths before enabling it.
- Use access-control modules when they fit the project's dependency and version constraints. Confirm module initialization and exports rather than copying an interface by name alone.
- Keep loops statically bounded. Vyper's integer operations are checked by default.
- NatSpec tags such as `@notice`, `@dev`, `@param`, and `@return` are optional. Add useful documentation to public-facing APIs; do not add empty or inaccurate tags. Internal-function docstrings are not included in compiler NatSpec output.
- Keep file organization readable and consistent with the repository. Vyper accepts flexible top-level declaration ordering; no universal two-blank-line rule is required.

## References

- [Types and flags](https://docs.vyperlang.org/en/stable/types.html#flags)
- [Statements and exceptions](https://docs.vyperlang.org/en/stable/statements.html#assertions-and-exceptions)
- [Control structures and decorators](https://docs.vyperlang.org/en/stable/control-structures.html)
- [Modules](https://docs.vyperlang.org/en/stable/using-modules.html)
- [NatSpec](https://docs.vyperlang.org/en/stable/natspec.html)
- [Style guide](https://docs.vyperlang.org/en/stable/style-guide.html)
- [Titanoboa dev revert reasons](https://titanoboa.readthedocs.io/en/latest/explain/revert_reasons/#dev-revert-reasons)
