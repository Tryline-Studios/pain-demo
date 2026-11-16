"""`python -m pain_demo validate ...`: the Validation CLI (spec section 18)."""

import sys

from pain_demo.cli import main

if __name__ == "__main__":  # the spawned XSD worker re-imports this module as __mp_main__
    sys.exit(main())
