---
name: vyper-testing
description: >
  Write, review, and generate advanced tests for Vyper smart contracts using Titanoboa (boa)
  and Moccasin. Use when writing test files, creating fixtures, generating fuzz tests, setting
  up gas profiling, computing coverage, testing blueprints/factories, or when the user asks
  about boa testing patterns, hypothesis strategies, pranking, staging markers, or private
  member access in Vyper contracts.
---

# Vyper Testing with Titanoboa & Moccasin

## Quick Start

Apply this skill when:

- Writing or reviewing `test_*.py` files for Vyper contracts
- Creating `conftest.py` fixtures for contract deployments
- Generating fuzz tests, gas profiles, or coverage reports
- Testing blueprint/factory patterns, access control, or token logic

Conventions:

- Tests live in `tests/`, shared fixtures in `tests/conftest.py`
- Files named `test_<module>.py`; functions named `test_<function>_<scenario>_<expected>`
- Use `import boa` as the primary testing runtime

## Core Testing Primitives

### Loading Contracts

```python
# Native import (Moccasin projects — preferred)
from src import my_contract
from src.blueprints import token

contract = my_contract.deploy(arg1, arg2)

# Direct load
contract = boa.load("src/my_contract.vy", arg1, arg2)

# From source string
contract = boa.loads(source_code, arg1, arg2)
```

### Blueprints and Factories

```python
blueprint = token.deploy_as_blueprint()

factory = factory_module.deploy(blueprint)

child_addr = factory.create_child("Name", "SYM")
child = token.at(child_addr)
```

### Identity and Pranking

```python
addr = boa.env.generate_address(alias="alice")
boa.env.set_balance(addr, 10 ** 18)

with boa.env.prank(addr):
    contract.restricted_function()
```

### Expecting Reverts

```python
# Match assert message
with boa.reverts("insufficient balance"):
    contract.transfer(to, amount)

# Match vm_error (assert with message)
with boa.reverts(vm_error="Not authorized"):
    contract.admin_only()

# Match compiler-level revert (e.g. underflow)
with boa.reverts(compiler="safesub"):
    contract.subtract(1, 2)

# Match dev comment: `assert x  # dev: reason`
with boa.reverts(dev="only owner"):
    contract.set_owner(addr)
```

### State Snapshots

`boa.env.anchor()` snapshots VM state and rolls back on exit:

```python
with boa.env.anchor():
    contract.mint(addr, 100)
    assert contract.balanceOf(addr) == 100
# state is reverted here
assert contract.balanceOf(addr) == 0
```

### Evaluating Vyper In-Context

```python
# Standalone evaluation
result = boa.eval("keccak256('hello')")

# Evaluate against a deployed contract's state
contract.eval("self.some_variable")
contract.eval("self._internal_var + 1")
```

### Forking

```python
with boa.fork("https://eth.llamarpc.com"):
    usdc = ERC20.at("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
    assert usdc.symbol() == "USDC"
```

### Token Balance Manipulation

```python
boa.deal(usdc, alice, 1_000 * 10 ** 6)
assert usdc.balanceOf(alice) == 1_000 * 10 ** 6
```

## Accessing Private Members

Boa exposes contract internals for white-box testing:

```python
# Internal functions
contract.internal._compute_hash(data)

# Private storage variables
contract._storage.my_var.get()

# Private immutables
contract._immutables.MY_CONST

# Module variables (Vyper 0.4+)
contract.eval("imported_module.x")
```

## Fixtures (conftest.py)

Structure fixtures in layers: accounts, roles, contracts, blueprints, factories.

```python
import pytest
import boa
from src import my_token
from src.blueprints import nft


@pytest.fixture(scope="session")
def accounts():
    accts = {}
    for i in range(5):
        addr = boa.env.generate_address(alias=f"user_{i}")
        boa.env.set_balance(addr, 10 ** 18)
        accts[f"user_{i}"] = addr
    return accts


@pytest.fixture
def owner(accounts):
    return accounts["user_0"]


@pytest.fixture
def user(accounts):
    return accounts["user_1"]


@pytest.fixture
def token_contract(owner):
    with boa.env.prank(owner):
        return my_token.deploy("Token", "TKN", 18, 1_000_000, owner)


@pytest.fixture
def nft_blueprint():
    return nft.deploy_as_blueprint()
```

Use `scope="session"` for expensive, read-only fixtures (accounts, blueprints). Use default function scope for contracts that tests mutate.

Moccasin projects can also wrap deploy scripts:

```python
from script.deploy import deploy_feed

@pytest.fixture(scope="session")
def price_feed():
    return deploy_feed()
```

## Fuzzing with Hypothesis

Import strategies from `boa.test.strategies`:

```python
from boa.test import strategies as boa_st
from hypothesis import given, settings


@given(amount=boa_st.uint256().filter(lambda x: 0 < x < 10 ** 20))
@settings(max_examples=200, deadline=None)
def test_deposit_any_amount(token, user, amount):
    with boa.env.prank(user):
        token.deposit(value=amount)
    assert token.balanceOf(user) >= amount
```

### Available Strategies

| Strategy | Description |
|----------|-------------|
| `boa_st.address()` | Valid Ethereum address |
| `boa_st.uint256()`, `uint128()`, `uint8()` | Unsigned integers within Vyper bounds |
| `boa_st.int128()`, `int256()` | Signed integers |
| `boa_st.bytes32()` | 32-byte values |
| `boa_st.bytes_(max_size=N)` | Variable-length bytes |
| `boa_st.string(max_size=N)` | Strings within Vyper limits |
| `boa_st.bool_()` | Boolean |
| `boa_st.decimal()` | Fixed-point decimal |
| `boa_st.array(strategy, size)` | Fixed-size array |
| `boa_st.dynamic_array(strategy, max_size=N)` | Dynamic array |

### Filtering for Realistic Values

```python
realistic_amount = boa_st.uint256().filter(lambda x: 10 ** 16 <= x <= 10 ** 21)

non_zero_addr = boa_st.address().filter(
    lambda x: x != "0x0000000000000000000000000000000000000000"
)
```

### Stateful Testing

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant


class TokenStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.token = boa.load("src/token.vy", "T", "T", 18, 0, boa.env.eoa)
        self.balances = {}
        self.total = 0

    @rule(acct=boa_st.address(), amt=boa_st.uint256().filter(lambda x: x < 10 ** 20))
    def mint(self, acct, amt):
        self.token.mint(acct, amt)
        self.balances[acct] = self.balances.get(acct, 0) + amt
        self.total += amt

    @invariant()
    def supply_matches(self):
        assert self.token.totalSupply() == self.total


TestToken = TokenStateMachine.TestCase
```

## Gas Profiling

### Per-Test Marker

```python
@pytest.mark.gas_profile
def test_expensive_op(contract):
    contract.batch_process(data)
```

### CLI (all tests)

```bash
pytest tests/ --gas-profile
```

Exclude specific tests with `@pytest.mark.ignore_gas_profiling`.

### Programmatic

```python
boa.env.enable_gas_profiling()
contract.operation()
boa.env.reset_gas_metering_behavior()
```

Output includes two tables: **call profile** (per-function stats) and **line profile** (per-line gas within functions), each showing count, mean, median, stdev, min, max.

## Coverage

### Setup

Add to `.coveragerc`:

```ini
[run]
plugins = boa.coverage
```

### Run

```bash
pytest --cov= --cov-branch tests/

# Moccasin shorthand
mox test --coverage
```

Coverage does not work with fast mode enabled.

## Moccasin-Specific Features

### Staging Markers

Run tests only on live networks:

```python
@pytest.mark.staging
@pytest.mark.ignore_isolation
def test_oracle_integration(price_feed):
    assert price_feed.latestAnswer() > 0
```

- `mox test` runs only non-staging tests
- `mox test --network sepolia` runs only `@pytest.mark.staging` tests
- Add `@pytest.mark.local` to also run staging tests on local networks

Networks with `live_or_staging = true` in `moccasin.toml` skip non-staging tests automatically.

## Test Organization Best Practices

### Structure

Follow Arrange-Act-Assert:

```python
def test_transfer_updates_balances(token, owner, user):
    # Arrange
    initial = token.balanceOf(owner)
    amount = 100

    # Act
    with boa.env.prank(owner):
        token.transfer(user, amount)

    # Assert
    assert token.balanceOf(owner) == initial - amount
    assert token.balanceOf(user) == amount
```

### Test Grouping

Organize tests by category within each file:

1. **Deployment / initial state** -- constructor values, default storage
2. **Happy path** -- normal operations succeed
3. **Access control** -- unauthorized callers revert
4. **Edge cases / reverts** -- zero values, max values, overflow, underflow
5. **Invariants / fuzzing** -- property-based tests at the bottom

### Naming

```
test_<function>_<scenario>_<expected>

test_transfer_zero_amount_reverts
test_mint_by_owner_succeeds
test_burn_exceeds_balance_reverts
```

### One Assertion Per Test

Prefer one logical assertion per test for clear failure messages. Multiple related asserts (e.g. sender and receiver balances after transfer) in one test are acceptable when they verify a single operation.

## Additional Resources

- For extended API reference and advanced patterns, see [reference.md](reference.md)
- [Titanoboa docs](https://titanoboa.readthedocs.io/)
- [Moccasin testing docs](https://cyfrin.github.io/moccasin/core_concepts/testing/)
- [Vyper docs](https://docs.vyperlang.org/)
