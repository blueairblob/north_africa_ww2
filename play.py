"""Windows review-build entry point; source users can still run python -m screen."""
import sys

from screen.__main__ import main


if __name__ == "__main__":
    main(sys.argv[1:])
