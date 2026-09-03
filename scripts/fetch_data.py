"""Future CLI for explicit, configuration-driven Open-Meteo acquisition."""


def main() -> None:
    """Refuse implicit downloads during Phase 0."""

    raise SystemExit("Data download is intentionally disabled in Phase 0.")


if __name__ == "__main__":
    main()
