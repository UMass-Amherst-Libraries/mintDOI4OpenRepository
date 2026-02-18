
import argparse
import getpass
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse, urlunparse, ParseResult


_REPO__ENDPOINT = "MINT__REPO__ENDPOINT"
_DC__API = "MINT__DATACITE__API"
_DC__TOKEN = "MINT__DATACITE__TOKEN"
_DC__PREFIX = "MINT__DATACITE__PREFIX"
_AFFIL__NAME = "MINT__AFFIL__NAME"
_AFFIL__ROR = "MINT__AFFIL__ROR"

_BATCH__RPS = "MINT__BATCH__RPS"
_BATCH__CONCURRENCY = "MINT__BATCH__CONCURRENCY"
_BATCH__RETRYCOUNT = "MINT__BATCH__RETRYCOUNT"

def _url_param(param: str) -> ParseResult:
    if "//" not in param:
        param = "//" + param
    return urlparse(param, scheme="https")

@dataclass
class ParsedArgs:
    repo_endpoint: ParseResult | None = None
    datacite_api: ParseResult | None = None
    datacite_token: str | None = None
    ask_datacite_token: bool = False

    prefix: str | None = None
    affiliation_name: str | None = None
    affiliation_ror: str | None = None

    rps: float = 5.0
    concurrency: int = 2
    retry_count: int = 3

    log_directory: Path = Path("./logs")
    run_directory: Path = Path("./runs")
    verbose: int = 0

    command: str | None = None
    data: Path | None = None
    additional_data: list[Path] | None = None

    @property
    def repo_url(self) -> str | None:
        if self.repo_endpoint is None:
            return None
        return urlunparse(self.repo_endpoint[:2] + ("", "", None, None)).rstrip("/")

    @property
    def datacite_base(self) -> str | None:
        if self.datacite_api is None:
            return None
        return urlunparse(self.datacite_api[:2] + ("", "", None, None)).rstrip("/")

    @property
    def data_location(self) -> dict[str, Path] | None:
        if self.data is None:
            return None
        all_data = [self.data] + (self.additional_data or [])
        locations: dict[str, Path] = {}

        for p in all_data:
            if p.is_file():
                locations[p.stem] = p
                continue
            if not p.exists():
                raise ValueError(f"{p} does not exist")
            # include csvs inside directories
            if p.is_dir():
                locations |= {sp.stem: sp for sp in p.glob("**/*.csv")}

        return locations if locations else None

    @staticmethod
    @lru_cache
    def parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="mintdoi",
            description="Batch mint DataCite DOIs from Open Repository/DSpace item UUID CSVs."
        )
        parser.add_argument("-v", "--verbose", action="count")
        parser.add_argument("--log-directory", type=Path, default=Path("./logs"))
        parser.add_argument("--run-directory", type=Path, default=Path("./runs"))

        g = parser.add_argument_group("Repository")
        g.add_argument("--repo-endpoint", type=_url_param,
                       help=f"Open Repository base url. Env: {_REPO__ENDPOINT}")

        g = parser.add_argument_group("DataCite")
        g.add_argument("--datacite-api", type=_url_param,
                       help=f"DataCite API base. Env: {_DC__API}")
        g.add_argument("--ask-datacite-token", action="store_true",
                       help=f"Prompt for token. Env alternative: {_DC__TOKEN}")
        g.add_argument("--prefix", type=str, help=f"DOI prefix. Env: {_DC__PREFIX}")

        g = parser.add_argument_group("Affiliation")
        g.add_argument("--affil-name", type=str, help=f"Env: {_AFFIL__NAME}")
        g.add_argument("--affil-ror", type=str, help=f"Env: {_AFFIL__ROR}")

        g = parser.add_argument_group("Batch")
        g.add_argument("--rps", type=float, help=f"DataCite requests/sec. Env: {_BATCH__RPS}")
        g.add_argument("--concurrency", type=int, help=f"Workers. Env: {_BATCH__CONCURRENCY}")
        g.add_argument("--retry-count", type=int, help=f"Retries. Env: {_BATCH__RETRYCOUNT}")

        commands = parser.add_subparsers(dest="command", metavar="command")
        commands.add_parser("check", help="Check CSV + connectivity")
        commands.add_parser("run", help="Transform + mint + patch")

        # input data
        parser.add_argument("data", type=Path, help="CSV file or directory containing CSVs")
        parser.add_argument("additional_data", nargs="*", type=Path, help="More CSVs or dirs (optional)")

        return parser

def main(argv: list[str] | None = None) -> int:
    args = ParsedArgs(
        repo_endpoint=_url_param(os.environ[_REPO__ENDPOINT]) if _REPO__ENDPOINT in os.environ else None,
        datacite_api=_url_param(os.environ[_DC__API]) if _DC__API in os.environ else None,
        datacite_token=os.environ.get(_DC__TOKEN),
        prefix=os.environ.get(_DC__PREFIX),
        affiliation_name=os.environ.get(_AFFIL__NAME),
        affiliation_ror=os.environ.get(_AFFIL__ROR),
        rps=float(os.environ.get(_BATCH__RPS, "5")),
        concurrency=int(os.environ.get(_BATCH__CONCURRENCY, "2")),
        retry_count=int(os.environ.get(_BATCH__RETRYCOUNT, "3")),
    )

    parser = ParsedArgs.parser()
    args = parser.parse_args(argv, namespace=args)

    if args.ask_datacite_token and not args.datacite_token:
        args.datacite_token = getpass.getpass("DataCite token: ").strip()
        if not args.datacite_token:
            print("DataCite token is required.", file=sys.stderr)
            return 2

    if args.command in ("check", "run"):
        if not args.repo_url or not args.datacite_base or not args.prefix:
            parser.print_usage()
            print("Missing required: repo-endpoint, datacite-api, prefix", file=sys.stderr)
            return 2
        if not args.data_location:
            parser.print_usage()
            print("No readable CSV data provided.", file=sys.stderr)
            return 2

    if args.command == "check":
        # TODO: call check logic (csv columns, uuid format, GET test, DataCite auth test)
        print("OK (stub): check passed")
        return 0

    if args.command == "run":
        # TODO: call pipeline batch runner
        print("OK (stub): run started")
        return 0

    parser.print_usage()
    return 2

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
