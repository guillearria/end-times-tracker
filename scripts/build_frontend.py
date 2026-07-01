#!/usr/bin/env python3
"""Aggregate threats and World Pulse events into frontend/data/{threats,events}.json."""

from pipeline import frontend


def main() -> None:
    threats = frontend.build()
    events = frontend.build_events()
    print(
        f"built frontend/data/threats.json — "
        f"{len(threats['published'])} published, {len(threats['under_review'])} under review\n"
        f"built frontend/data/events.json — "
        f"{len(events['published'])} published, {len(events['under_review'])} under review"
    )


if __name__ == "__main__":
    main()
