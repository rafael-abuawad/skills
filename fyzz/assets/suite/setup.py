"""Replace with the project's real deployments, roles, balances, and approvals."""


def deploy(config):
    # Runs inside each state-machine instance's isolated chain context.
    # A fixture may supply a different zero-argument factory; never share mutable
    # deployed state across Hypothesis examples without restoring it here.
    raise NotImplementedError("Wire protocol deployment before running Fyzz")
