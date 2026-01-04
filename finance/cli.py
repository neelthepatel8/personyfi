import argparse
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

from .config import load_config
from . import db
from .doctor import run_doctor
from .ingest import ingest_all, ingest_one_account
from .logging_config import configure_logging
from .api_server import serve_api


def main() -> int:
    parser = argparse.ArgumentParser(prog="finance")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Verify config, DB, and Teller connectivity")

    ingest_parser = subparsers.add_parser("ingest", help="Sync transactions via Teller")
    ingest_parser.add_argument("--account-id", help="Limit ingest to a single account")
    ingest_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    ingest_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    ingest_parser.add_argument("--lookback-days", type=int, help="Days to look back")
    ingest_parser.add_argument(
        "--full",
        action="store_true",
        help="Full sync using stored cursor (ignores date filters)",
    )
    ingest_parser.add_argument(
        "--page-size",
        type=int,
        help="Transactions per request",
    )

    subparsers.add_parser("inbox", help="Show review inbox")

    serve_parser = subparsers.add_parser(
        "serve",
        help="Run local HTTP API and optional scheduled ingest loop",
    )
    serve_parser.add_argument("--host", help="API host (default from env)")
    serve_parser.add_argument("--port", type=int, help="API port (default from env)")
    serve_parser.add_argument(
        "--interval-minutes",
        type=int,
        help="Scheduled ingest interval in minutes",
    )
    serve_parser.add_argument(
        "--lookback-days",
        type=int,
        help="Scheduled ingest lookback window in days",
    )
    serve_parser.add_argument("--page-size", type=int, help="Scheduled ingest page size")
    serve_parser.add_argument(
        "--no-schedule", action="store_true", help="Disable scheduled ingest loop"
    )

    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Remove non-Teller records from the database"
    )
    cleanup_parser.add_argument(
        "--force",
        action="store_true",
        help="Delete records (omit to preview only)",
    )


    args = parser.parse_args()
    load_dotenv()
    configure_logging(args.verbose)
    config = load_config()

    if args.command == "doctor":
        return run_doctor(config)
    if args.command == "ingest":
        return _handle_ingest(config, args)
    if args.command == "inbox":
        from .inbox import run_inbox

        return run_inbox(config.db_path)
    if args.command == "serve":
        return serve_api(
            config,
            host=args.host,
            port=args.port,
            interval_minutes=args.interval_minutes,
            lookback_days=args.lookback_days,
            page_size=args.page_size,
            schedule=not args.no_schedule,
        )
    if args.command == "cleanup":
        return _handle_cleanup(config, args)
    parser.print_help()
    return 1


def _handle_ingest(config, args) -> int:
    try:
        page_size = args.page_size or config.ingest_page_size
        if args.full:
            start_date = None
            end_date = None
        elif args.start_date or args.end_date:
            start_date = args.start_date
            end_date = args.end_date
        else:
            lookback_days = args.lookback_days or config.ingest_lookback_days
            if lookback_days < 1:
                raise ValueError("lookback_days must be >= 1")
            today = date.today()
            start_date = (today - timedelta(days=lookback_days)).isoformat()
            end_date = today.isoformat()

        if args.account_id:
            ingest_one_account(
                config,
                args.account_id,
                start_date=start_date,
                end_date=end_date,
                page_size=page_size,
            )
        else:
            ingest_all(
                config,
                start_date=start_date,
                end_date=end_date,
                page_size=page_size,
            )
    except Exception as exc:
        print(f"Ingest failed: {exc}")
        return 1
    return 0


def _handle_cleanup(config, args) -> int:
    conn = db.connect(config.db_path)
    db.init_db(conn)
    counts = db.cleanup_non_item(conn, "teller", dry_run=not args.force)
    action = "Would delete" if not args.force else "Deleted"
    print(
        f"{action} transaction_raw={counts['transaction_raw']} "
        f"transactions={counts['transactions']} accounts={counts['accounts']} "
        f"items={counts['items']} account_sync={counts['account_sync']}"
    )
    if not args.force:
        print("Re-run with --force to delete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
