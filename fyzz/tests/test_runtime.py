"""Exercise generated runtime contracts, plus real Hypothesis/Titanoboa integration."""
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import sys

import pytest

pytest.importorskip("hypothesis")
from hypothesis import settings, strategies as st
from hypothesis.stateful import invariant, rule, run_state_machine_as_test

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "suite"
spec = importlib.util.spec_from_file_location("fyzz_suite_template", ASSETS / "__init__.py", submodule_search_locations=[str(ASSETS)])
package = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = package
spec.loader.exec_module(package)
from fyzz_suite_template.machine import ProtocolMachine
from fyzz_suite_template import machine as machine_module
from fyzz_suite_template.runtime import Diagnostics, campaign_settings, replay_value


def config(tmp_path):
    return {"framework": "boa", "meta_dir": str(tmp_path / "custom-metadata")}


class MinimalMachine(ProtocolMachine):
    @rule()
    def action(self):
        pass


def test_profiles_and_database(tmp_path, monkeypatch):
    for profile, expected in [("smoke", (10, 20)), ("standard", (100, 50)), ("extended", (1000, 100))]:
        monkeypatch.setenv("FYZZ_PROFILE", profile)
        selected = campaign_settings(config(tmp_path))
        assert (selected.max_examples, selected.stateful_step_count) == expected
        assert selected.deadline is None
    monkeypatch.setenv("FYZZ_MAX_EXAMPLES", "2")
    monkeypatch.setenv("FYZZ_STEPS", "3")
    assert campaign_settings(config(tmp_path)).max_examples == 2
    monkeypatch.setenv("FYZZ_STEPS", "0")
    with pytest.raises(ValueError):
        campaign_settings(config(tmp_path))


def test_initialization_failure_releases_isolation(tmp_path, monkeypatch):
    active = []
    @contextmanager
    def isolated(_):
        active.append(True)
        try:
            yield
        finally:
            active.pop()
    monkeypatch.setattr(machine_module, "isolation", isolated)
    def bad_deployment():
        assert active
        raise RuntimeError("deployment failed")
    with pytest.raises(RuntimeError, match="deployment failed"):
        MinimalMachine(config(tmp_path), bad_deployment)
    assert not active


def test_models_are_fresh_and_teardown_survives_log_failure(tmp_path, monkeypatch):
    active = []
    @contextmanager
    def isolated(_):
        active.append(True)
        try:
            yield
        finally:
            active.pop()
    monkeypatch.setattr(machine_module, "isolation", isolated)
    first = MinimalMachine(config(tmp_path), lambda: {})
    first.model.balances["alice"] = 5
    first.teardown()
    second = MinimalMachine(config(tmp_path), lambda: {})
    assert second.model.balances == {}
    def broken_save():
        raise OSError("disk full")
    monkeypatch.setattr(second.diagnostics, "save", broken_save)
    with pytest.raises(OSError):
        second.teardown()
    assert not active


def test_action_postcondition_trace_and_expected_revert(tmp_path):
    diagnostics = Diagnostics(config(tmp_path))
    class ContractRevert(Exception):
        pass
    with diagnostics.action("unauthorized", inputs={"actor": "0x01"}, expected_revert=(ContractRevert,), match="permission"):
        raise ContractRevert("permission denied")
    with diagnostics.action("deposit", inputs={"amount": 2}, transition="empty-funded"):
        pass
    with pytest.raises(AssertionError, match="bad postcondition"):
        with diagnostics.action("withdraw", inputs={"amount": 2, "data": b"\x01"}):
            raise AssertionError("bad postcondition")
    diagnostics.save()
    trace = json.loads(next((diagnostics.root / "traces").glob("*.json")).read_text())
    assert [x["outcome"] for x in trace["actions"]] == ["expected_revert", "success", "failure"]
    assert trace["counts"]["deposit:successes"] == 1
    assert trace["actions"][-1]["inputs"]["data"] == {"bytes_hex": "01"}
    assert trace["transitions"] == {"empty-funded": 1}
    with pytest.raises(TypeError):
        with diagnostics.action("unsafe", inputs={}, expected_revert=(Exception,)):
            pass
    with pytest.raises(AssertionError, match="did not occur"):
        with diagnostics.action("missing", inputs={}, expected_revert=(ContractRevert,)):
            pass
    with pytest.raises(TypeError):
        replay_value(object())


def test_unfinished_scaffold_cannot_pass(tmp_path):
    with pytest.raises(Exception, match="no rules"):
        ProtocolMachine(config(tmp_path), lambda: {})


VYPER = '''
#pragma version ^0.4.0
owner: public(address)
total: public(uint256)

@deploy
def __init__():
    self.owner = msg.sender

@external
def add(amount: uint256):
    assert msg.sender == self.owner, "owner"
    self.total += amount + BUG
'''


@pytest.mark.parametrize("bug", [0, 1])
def test_real_boa_hypothesis_isolation_shrinking_and_repro(tmp_path, bug):
    boa = pytest.importorskip("boa")
    initial_sender = boa.env.eoa
    deployments = []
    def deploy():
        contract = boa.loads(VYPER.replace("BUG", str(bug)))
        assert contract.total() == 0
        deployments.append(contract.address)
        return contract
    class CounterMachine(ProtocolMachine):
        @rule(amount=st.integers(min_value=1, max_value=5))
        def add(self, amount):
            with self.diagnostics.action("add", inputs={"amount": amount, "actor": str(initial_sender)}, transition="increase"):
                self.deployment.add(amount)
                self.model.balances["sum"] = self.model.balances.get("sum", 0) + amount
        @rule()
        def unauthorized(self):
            with self.diagnostics.action("unauthorized", inputs={"actor": str(boa.env.generate_address())}, expected_revert=(boa.BoaError,), match="owner"):
                with boa.env.prank(boa.env.generate_address()):
                    self.deployment.add(1)
        @invariant()
        def total(self):
            """fyzz: GL-01"""
            def check():
                assert self.deployment.total() == self.model.balances.get("sum", 0), "GL-01"
            self.diagnostics.check("GL-01", check)
    run = lambda: run_state_machine_as_test(lambda: CounterMachine(config(tmp_path), deploy), settings=settings(max_examples=10, stateful_step_count=8, deadline=None, database=None, derandomize=True))
    if bug:
        with pytest.raises(AssertionError, match="GL-01"):
            run()
        traces = [json.loads(path.read_text()) for path in (Path(config(tmp_path)["meta_dir"]) / "traces").glob("*.json")]
        shortest = min((trace for trace in traces if trace["failure"].get("spec_id") == "GL-01"), key=lambda trace: len(trace["actions"]))
        assert len(shortest["actions"]) == 1
        assert shortest["actions"][0]["inputs"]["amount"] == 1
        # Replay the minimized concrete inputs under a fresh anchor.
        with boa.env.anchor():
            contract = deploy()
            amount = shortest["actions"][0]["inputs"]["amount"]
            contract.add(amount)
            with pytest.raises(AssertionError, match="GL-01"):
                assert contract.total() == amount, "GL-01"
    else:
        run()
    assert len(deployments) > 1
    assert boa.env.eoa == initial_sender
    assert boa.env.get_code(deployments[-1]) == b""
