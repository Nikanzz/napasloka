"""Future CLI for reproducible exploratory data analysis."""


def main() -> None:
    """Avoid generating EDA results before processed data exists."""

    raise SystemExit("EDA is not executed during Phase 0.")


if __name__ == "__main__":
    main()
