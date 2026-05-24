from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = [
    ("NotaryIdentityRegistry", ROOT / "contracts" / "NotaryIdentityRegistry.sol"),
    ("AttestationRegistry", ROOT / "contracts" / "AttestationRegistry.sol"),
    ("NotaryValidationRegistry", ROOT / "contracts" / "NotaryValidationRegistry.sol"),
    ("NotaryGovernance", ROOT / "contracts" / "NotaryGovernance.sol"),
    ("NotaryKarma", ROOT / "contracts" / "NotaryKarma.sol"),
    ("NotaryAgentIdentity", ROOT / "contracts" / "NotaryAgentIdentity.sol"),
    ("NotaryReplication", ROOT / "contracts" / "NotaryReplication.sol"),
]


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def deploy_contract(contract_name: str, contract_file: Path, rpc_url: str, private_key: str) -> dict[str, str]:
    if not shutil.which("forge"):
        raise RuntimeError("forge is not installed or not on PATH")
    command = [
        "forge",
        "create",
        "--rpc-url",
        rpc_url,
        "--private-key",
        private_key,
        "--broadcast",
        f"{contract_file}:{contract_name}",
    ]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"forge create failed for {contract_name}")

    address = ""
    tx_hash = ""
    for line in proc.stdout.splitlines():
        if line.startswith("Deployed to:"):
            address = line.split(":", 1)[1].strip()
        if line.startswith("Transaction hash:"):
            tx_hash = line.split(":", 1)[1].strip()
    if not address:
        raise RuntimeError(f"Could not parse deployment address for {contract_name}")
    return {"contract": contract_name, "address": address, "txHash": tx_hash}


def main() -> None:
    rpc_url = _require_env("ARC_RPC_URL")
    private_key = _require_env("ARC_OPERATOR_PRIVATE_KEY")
    deployments = [deploy_contract(name, path, rpc_url, private_key) for name, path in CONTRACTS]
    print(json.dumps({"deployments": deployments}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
