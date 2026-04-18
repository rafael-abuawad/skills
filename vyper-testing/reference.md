# Vyper Testing Reference

Extended API reference and advanced patterns for Titanoboa and Moccasin testing.

## boa.env API Cheat Sheet

### Account Management

| Method | Description |
|--------|-------------|
| `boa.env.generate_address(alias="name")` | Generate a new address, optionally aliased |
| `boa.env.alias(address, "name")` | Alias an existing address for readable tracebacks |
| `boa.env.lookup_alias(address)` | Get the alias for an address |
| `boa.env.set_balance(addr, wei)` | Set ETH balance |
| `boa.env.get_balance(addr)` | Get ETH balance |
| `boa.env.eoa` | Current default sender address |

### Pranking

```python
with boa.env.prank(addr):
    # msg.sender == addr for all calls in this block
    contract.do_something()
# msg.sender reverts to boa.env.eoa
```

### State Management

| Method | Description |
|--------|-------------|
| `boa.env.anchor()` | Context manager: snapshot state, rollback on exit |
| `boa.env.time_travel(seconds=N)` | Advance block timestamp by N seconds |
| `boa.env.time_travel(blocks=N)` | Advance block number by N blocks |
| `boa.env.time_travel(seconds=N, blocks=M)` | Advance both timestamp and block number |
| `boa.env.get_storage(addr, slot)` | Read raw storage slot |
| `boa.env.set_storage(addr, slot, value)` | Write raw storage slot (use with caution) |
| `boa.env.get_code(addr)` | Get deployed bytecode |
| `boa.env.set_code(addr, bytecode)` | Overwrite bytecode at address |
| `boa.env.timestamp` | Current block timestamp |

### Gas Metering

| Method | Description |
|--------|-------------|
| `boa.env.enable_gas_profiling()` | Switch to `ProfilingGasMeter` |
| `boa.env.disable_gas_metering()` | Switch to `NoGasMeter` |
| `boa.env.reset_gas_metering_behavior()` | Restore default `GasMeter` |
| `boa.env.get_gas_used()` | Total gas consumed |
| `boa.env.reset_gas_used()` | Reset gas counter to zero |
| `boa.env.gas_meter_class(cls)` | Context manager for temporary gas meter |

### Low-Level Execution

| Method | Description |
|--------|-------------|
| `boa.env.raw_call(to, data=, value=, sender=, gas=)` | Execute call, raises on revert |
| `boa.env.execute_code(bytecode=, at=, data=, sender=)` | Execute bytecode, returns `ComputationAPI` |
| `boa.env.deploy_code(bytecode=, at=, sender=)` | Deploy bytecode at address |

### Forking

```python
with boa.fork("https://eth.llamarpc.com", block_identifier="safe"):
    # Interact with mainnet state
    contract = boa.load("src/my_contract.vy")

# Options:
# block_identifier: int | "safe" | "latest" | "finalized"
# cache_dir: str | None (default: ~/.cache/titanoboa/fork/)
# allow_dirty: bool (default: False)
```

### Token Manipulation (forked environments)

```python
boa.deal(token_contract, receiver_addr, amount)
boa.deal(token_contract, receiver_addr, amount, adjust_supply=False)
```

## Contract Instance API

### Deployed Contract

```python
contract = my_module.deploy(arg1, arg2)

# Call external functions
result = contract.my_view_function()
contract.my_state_function(arg)

# Evaluate arbitrary Vyper against this contract's state
contract.eval("self.x + self.y")

# Get logs emitted by the last transaction
logs = contract.get_logs()

# Access ABI
contract.abi
```

### Private Members

```python
# Internal functions
contract.internal._my_internal_fn(arg1, arg2)

# Private storage
val = contract._storage.my_private_var.get()

# Private immutables
val = contract._immutables.MY_IMMUTABLE

# Module-level variables (Vyper 0.4+)
contract.eval("my_module.some_var")
```

### Blueprint Deployment

```python
from src.blueprints import token

# Deploy as blueprint (ERC-5202)
blueprint = token.deploy_as_blueprint()

# In factory tests, pass blueprint to factory constructor
factory = factory_module.deploy(blueprint)

# After factory creates a child, bind to it
child_addr = factory.create_child("Name", "SYM")
child = token.at(child_addr)
assert child.name() == "Name"
```

## Revert Matching Reference

| Parameter | Matches | Example |
|-----------|---------|---------|
| Positional `reason` | Both `raise` messages and `# dev:` comments | `boa.reverts("msg")` |
| `vm_error=` | `assert` messages (`assert x, "msg"`) | `boa.reverts(vm_error="Not owner")` |
| `compiler=` | Compiler-generated checks (overflow, etc.) | `boa.reverts(compiler="safesub")` |
| `dev=` | Developer comments (`assert x  # dev: msg`) | `boa.reverts(dev="only admin")` |

## Hypothesis Strategies — Advanced

### Composite Strategies

```python
from hypothesis import strategies as st
from boa.test import strategies as boa_st

transfer_data = st.tuples(
    boa_st.address(),
    boa_st.address(),
    boa_st.uint256().filter(lambda x: 0 < x < 10 ** 20),
)

@given(data=transfer_data)
@settings(max_examples=300, deadline=None)
def test_transfer(token, data):
    sender, recipient, amount = data
    token.mint(sender, amount * 2)
    with boa.env.prank(sender):
        token.transfer(recipient, amount)
    assert token.balanceOf(recipient) == amount
```

### Tuple Strategy (struct-like)

```python
position = boa_st.tuple_(boa_st.uint256(), boa_st.uint256(), boa_st.bool_())

@given(pos=position)
def test_position(contract, pos):
    amount, price, is_long = pos
    contract.open_position(amount, price, is_long)
```

### Full Stateful Testing Example

```python
import boa
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize
from boa.test import strategies as boa_st
from hypothesis import settings


class VaultStateMachine(RuleBasedStateMachine):
    @initialize()
    def setup(self):
        self.vault = boa.load("src/vault.vy", boa.env.eoa)
        self.deposits = {}
        self.total_deposits = 0

    @rule(
        user=boa_st.address().filter(
            lambda x: x != "0x0000000000000000000000000000000000000000"
        ),
        amount=boa_st.uint256().filter(lambda x: 0 < x < 10 ** 20),
    )
    def deposit(self, user, amount):
        boa.env.set_balance(user, amount)
        with boa.env.prank(user):
            self.vault.deposit(value=amount)
        self.deposits[user] = self.deposits.get(user, 0) + amount
        self.total_deposits += amount

    @rule(
        user=boa_st.address(),
        amount=boa_st.uint256().filter(lambda x: 0 < x < 10 ** 20),
    )
    def withdraw(self, user, amount):
        if self.deposits.get(user, 0) >= amount:
            with boa.env.prank(user):
                self.vault.withdraw(amount)
            self.deposits[user] -= amount
            self.total_deposits -= amount

    @invariant()
    def vault_balance_matches(self):
        assert boa.env.get_balance(self.vault.address) == self.total_deposits

    @invariant()
    def individual_balances_match(self):
        for user, expected in self.deposits.items():
            assert self.vault.balanceOf(user) == expected


TestVault = VaultStateMachine.TestCase
TestVault.settings = settings(max_examples=100, stateful_step_count=20)
```

## Gas Profiling — Advanced

### Programmatic Access to Profile Data

```python
from boa.profiling import get_line_profile_table, get_call_profile_table, global_profile

@pytest.mark.gas_profile
def test_gas_analysis(contract):
    for i in range(50):
        contract.process(i)

    profiles = global_profile().call_profiles
    for (addr, fn_name), profile in profiles.items():
        if fn_name == "process":
            assert profile.mean < 50_000, f"process() too expensive: {profile.mean}"
```

### Temporary Profiling Context

```python
from boa.vm.gas_meters import ProfilingGasMeter

def test_specific_profiling(contract):
    with boa.env.gas_meter_class(ProfilingGasMeter):
        contract.expensive_operation()
        from boa.profiling import get_call_profile_table
        print(get_call_profile_table())
```

### Comparing Implementations

```python
@pytest.mark.gas_profile
def test_compare_gas(v1_contract, v2_contract):
    for i in range(100):
        v1_contract.compute(i)
        v2_contract.compute(i)
    # Profile output will show separate tables for each contract
```

## Forking Test Patterns

### Testing Against Live Tokens

```python
import os
import boa

def test_swap_on_mainnet():
    with boa.fork(os.environ["ETH_RPC_URL"]):
        usdc = boa.load_partial("src/interfaces/IERC20.vy").at(
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        )
        alice = boa.env.generate_address("alice")
        boa.deal(usdc, alice, 10_000 * 10 ** 6)

        with boa.env.prank(alice):
            my_dex = boa.load("src/dex.vy")
            usdc.approve(my_dex.address, 10_000 * 10 ** 6)
            my_dex.swap(usdc.address, 1_000 * 10 ** 6)
```

### Anchored Fork State

```python
def test_multiple_scenarios_on_fork():
    with boa.fork(os.environ["ETH_RPC_URL"]):
        contract = boa.load("src/oracle_consumer.vy")

        with boa.env.anchor():
            contract.consume_price()
            assert contract.last_price() > 0

        with boa.env.anchor():
            contract.consume_price_with_staleness_check()
```

## CI/CD Integration

### GitHub Actions Gas Report

```yaml
name: Gas Report
on: [pull_request]

jobs:
  gas-profile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install moccasin
      - run: mox install
      - run: pytest tests/ --gas-profile -v > gas-report.txt
      - uses: actions/upload-artifact@v4
        with:
          name: gas-report
          path: gas-report.txt
```

### Coverage in CI

```yaml
- run: pytest tests/ --cov= --cov-branch --cov-report=term-missing
```

## Common Test Patterns

### Access Control Matrix

```python
def test_only_owner_can_set_fee(contract, owner, user):
    with boa.env.prank(owner):
        contract.set_fee(100)
    assert contract.fee() == 100

    with boa.env.prank(user):
        with boa.reverts():
            contract.set_fee(200)
    assert contract.fee() == 100
```

### Event Verification

```python
def test_transfer_emits_event(token, owner, user):
    with boa.env.prank(owner):
        token.transfer(user, 50)

    logs = token.get_logs()
    assert len(logs) == 1
    assert logs[0].event_type.name == "Transfer"
    assert logs[0].args.sender == owner
    assert logs[0].args.receiver == user
    assert logs[0].args.amount == 50
```

### Boundary Testing

```python
def test_mint_at_max_supply(nft, owner, max_supply):
    with boa.env.prank(owner):
        for i in range(max_supply):
            nft.mint(owner)

        with boa.reverts():
            nft.mint(owner)

    assert nft.totalSupply() == max_supply
```

### Multi-User Scenario

```python
def test_auction_lifecycle(auction, seller, bidder1, bidder2):
    with boa.env.prank(seller):
        auction.create(item_id=1, reserve=100)

    with boa.env.prank(bidder1):
        auction.bid(item_id=1, value=150)

    with boa.env.prank(bidder2):
        auction.bid(item_id=1, value=200)

    with boa.env.prank(seller):
        auction.finalize(item_id=1)

    assert auction.winner(1) == bidder2
```

## Deployment and Verification

### Network Deployment

```python
import boa
from eth_account import Account

boa.set_network_env("https://eth-sepolia.g.alchemy.com/v2/KEY")

account = Account.from_key("0x...")
boa.env.add_account(account)

contract = boa.load("src/MyContract.vy", arg1, arg2)
print(f"Deployed at: {contract.address}")
```

### Contract Verification

| Method | Description |
|--------|-------------|
| `boa.verify(contract, etherscan_api_key=KEY)` | Verify a single deployed contract on Etherscan |
| `boa.set_verifier("etherscan", api_key=KEY)` | Set a global verifier so all subsequent deploys are auto-verified |

### Mock Contracts (inline Vyper)

Use `boa.loads()` to create lightweight mocks without separate `.vy` files:

```python
mock_token = boa.loads("""
balances: HashMap[address, uint256]
totalSupply: uint256

@external
def mint(to: address, amount: uint256):
    self.balances[to] += amount
    self.totalSupply += amount

@external
@view
def balanceOf(account: address) -> uint256:
    return self.balances[account]
""")
```
