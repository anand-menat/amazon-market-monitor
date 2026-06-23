import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.automation import run_scrape_job


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a one-off Amazon scrape automation job.")
    parser.add_argument("--asin", required=True)
    parser.add_argument("--domain", default="com")
    parser.add_argument("--country", default="us", dest="country_code")
    parser.add_argument("--pages", type=int, default=2)
    parser.add_argument("--with-competitors", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run = run_scrape_job(
        {
            "asin": args.asin,
            "domain": args.domain,
            "country_code": args.country_code,
            "pages": args.pages,
            "with_competitors": args.with_competitors,
        }
    )
    print(run)
    raise SystemExit(0 if run["status"] == "success" else 1)


if __name__ == "__main__":
    main()
