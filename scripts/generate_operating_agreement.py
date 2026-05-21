from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notary.legal.operating_agreement import generate_operating_agreement


def main() -> None:
    agreement = generate_operating_agreement("notary_demo")
    print(json.dumps(agreement.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
