import asyncio
import getopt
import os
import pathlib
import sys
import time
import uuid

import pygit2
import requests

from liualgotrader.common import config
from liualgotrader.common.database import create_db_connection
from liualgotrader.models.accounts import Accounts
from liualgotrader.models.portfolio import Portfolio


def show_version():
    print(f"Liu Algo Trading Framework v{config.build_label}")


def show_usage():
    show_version()

    print()
    print("usage:")
    print("\t liu quickstart")
    print("\t OR")
    print("\t liu create portfolio <amount> [--credit=<credit>]")
    print("\n")
    print("options:")
    print("\t--credit\tAccount credit line")
    print()


def setup_db(
    db_location: str,
    db_name: str,
    user_name: str,
    password: str,
    restore_sample_db: bool,
):
    try:
        print()
        print("+---------------------+")
        print("| setting up database |")
        print("+---------------------+")
        print()

        p = pathlib.Path(db_location)
        if not p.exists():
            p.mkdir()
        if db_location[-1] != "/":
            db_location += "/"

        print("downloading files..")
        if os.name == "nt":
            r = requests.get(
                "https://raw.github.com/amor71/LiuAlgoTrader/master/database/docker-compose-windows.yml"
            )
        else:
            r = requests.get(
                "https://raw.github.com/amor71/LiuAlgoTrader/master/database/docker-compose.yml"
            )
        resolved = (
            r.text.replace("{db_name}", db_name)
            .replace("{user_name}", user_name)
            .replace("{password}", password)
        )

        with open(f"{db_location}docker-compose.yml", "w") as f:
            f.write(resolved)
            f.write("\n")

        base_url = (
            "https://raw.github.com/amor71/LiuAlgoTrader/master/database/"
        )
        files = ["schema.sql", "postgres.conf"]
        if restore_sample_db:
            files.append("liu_dump.sql")

        for file in files:
            r = requests.get(f"{base_url}{file}")
            with open(f"{db_location}{file}", "w", encoding="utf-8") as f:
                f.write(r.text)
                f.write("")
    except Exception as e:
        print(f"Something went wrong:{e}")
        print(
            "Pls open a new issue w/ details 'https://github.com/amor71/LiuAlgoTrader/issues/new'"
        )
        exit(0)

    print("files loaded successfully.")
    print(f"running docker-compose from within {db_location}:")
    to_run = f"cd {db_location} && docker-compose up -d"
    print("> ", to_run)
    os.system(to_run)

    if restore_sample_db:
        print("waiting for database to complete setup. 2 minutes")
        time.sleep(120)
        print("restoring sample database")
        to_run = f"cd {db_location} && docker exec -i pg-docker psql -q -U liu -W liu liu < liu_dump.sql"
        print("> ", to_run)
        os.system(to_run)
    print()
    print("check deployment using `\psql -h localhost -p 5400 -U liu`")


def setup_samples(
    samples_location: str, user: str, passwd: str, db: str
) -> None:
    try:
        print()
        print("+--------------------+")
        print("| setting up samples |")
        print("+--------------------+")

        p = pathlib.Path(samples_location)
        if not p.exists():
            p.mkdir()
        if samples_location[-1] != "/":
            samples_location += "/"

        base_url = "https://raw.github.com/amor71/LiuAlgoTrader/master/examples/quickstart/"
        files = [
            "tradeplan.toml",
            "vwap_short.py",
            "momentum_long_simplified.py",
        ]

        for file in files:
            print(f"Downloading {base_url}{file} to {samples_location}...")
            r = requests.get(f"{base_url}{file}")
            with open(f"{samples_location}{file}", "w") as f:
                f.write(r.text)
                f.write("")

        print()
        print("creating environment variables script")

        if os.name == "nt":
            with open(f"{samples_location}env_vars.bat", "w") as f:
                f.write(
                    f"set DSN=postgresql://{user}:{passwd}@localhost:5400/{db}\n"
                )
        else:
            with open(f"{samples_location}env_vars.sh", "w") as f:
                f.write(
                    f"export DSN=postgresql://{user}:{passwd}@localhost:5400/{db}\n"
                )

    except Exception as e:
        print(f"Something went wrong:{e}")
        print(
            "Pls open a new issue w/ details 'https://github.com/amor71/LiuAlgoTrader/issues/new'"
        )
        exit(0)


def quickstart():
    print(f"Welcome to Lig Algo Trading Framework v{config.build_label}!")
    print()
    print("This wizard will guide you through the setup process.")
    print()
    print("+----------------------------------------+")
    print("| Step #1 - Alpaca & Polygon credentials |")
    print("+----------------------------------------+")
    print()
    print(
        "To use Liu Algo Trading Framework you need an account with Alpaca Markets,"
    )
    print("do you already have an account [Y]/n:")
    i = input()
    have_funded = len(i) == 0 or (i == "y" or i == "Y" or i.lower() == "yes")

    if not have_funded:
        print("For additional details `https://alpaca.markets/docs/about-us/`")
        return

    to_exit = False
    if not config.alpaca_api_key or not config.alpaca_api_secret:
        print(
            "Liu Algo Trading Framework uses Alpaca for both LIVE and PAPER trading."
        )
        print()
        print("The Framework expects three environment variables to be set:")
        print(
            "`APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`: reflecting the funded"
        )
        print("account's API key and secret respectively.")
        print(
            "And `APCA_API_BASE_URL` reflecting the base URL for your account."
        )
        print(
            "Please set the three environment variables and re-run the wizard."
        )
        to_exit = True

    if to_exit:
        sys.exit(0)

    print()
    print("+----------------------------------+")
    print("| Step #2 - Database configuration |")
    print("+----------------------------------+")
    print()
    print("Do you already have a PostgreSQL instance configured [N]/y:")
    i = input()
    already_have_db = len(i) > 0 and (
        i == "y" or i == "Y" or i.lower() == "yes"
    )

    if already_have_db:
        print(
            "Follow the instructions at 'https://liualgotrader.readthedocs.io/en/latest/(Advanced)%20Setup.html#database-setup' to complete your database setup."
        )
        restore_sample_db = False
    else:
        pwd = pathlib.Path().absolute()
        print(
            "Liu Algo Trading Framework uses `docker-compose` to run a local database."
        )
        print(
            "The installation will download the docker-compose.yml, database schema"
        )
        print(
            "and prepare the database for first time usage. You can stop and re-run"
        )
        print(
            "the database using `docker-compose up -d ` and `docker-compose down`"
        )
        print(
            "respectively. Your data will not be deleted. For more details RTFM."
        )
        print()
        print(f"Select location for database files [{pwd}/liu_data/]:")
        db_location = input()
        db_location = (
            f"{pwd}/liu_data/" if not len(db_location) else db_location
        )

        print()
        print("** IMPORTANT NOTE**")
        print(
            "The installation wizard, aside from installing PostgreSQL in a docker"
        )
        print(
            "may also download a sample database, with existing data to help you"
        )
        print("take your first steps with Liu Algo Trading Framework.")
        print(
            "However, in order to restore the sample data, you need to select"
        )
        print(
            "the default username ('liu') password ('liu)', and database name ('liu')."
        )
        print(
            "after you try out the sample, you can delete data and re-run this"
        )
        print("wizard to install a fresh copy of the database.")
        print()
        print("Would you like to download the sample database? [Y]/n")
        i = input()
        restore_sample_db = len(i) == 0 or (
            i == "y" or i == "Y" or i.lower() == "yes"
        )
        print(
            "Select the database name for keeping track of your trading [liu]:"
        )
        db_name = input()
        db_name = "liu" if not len(db_name) else db_name
        print("Select the database user-name [liu]:")
        user_name = input()
        user_name = "liu" if not len(user_name) else user_name
        print("Select the database password [liu]:")
        password = input()
        password = "liu" if not len(password) else password

    print()
    print("+--------------------+")
    print("| Step #3 - Examples |")
    print("+--------------------+")
    print()
    print("Would you like to download & view samples? [Y]/n:")
    i = input()
    samples = not len(i) or i.lower() in ("y", "yes")
    sample_location = None
    if samples:
        pwd = pathlib.Path().absolute()
        print(f"Select location for sample files [{pwd}/liu_samples]:")
        sample_location = input()
        sample_location = (
            f"{pwd}/liu_samples"
            if not len(sample_location)
            else sample_location
        )

    print()
    print("Ready to go?? Press [ENTER] to start the installation..")
    input()

    if not already_have_db:
        setup_db(db_location, db_name, user_name, password, restore_sample_db)
    if samples:
        setup_samples(sample_location, user_name, password, db_name)
    print("setup completed successfully.")
    print()
    print()
    print("+---------------+")
    print("| what's next?  |")
    print("+---------------+")
    print()
    print("Congratulations, Liu Algo Trader is ready to go!")
    print(
        "From here, you can either run the back-testing UI, or read the docs."
    )
    print(
        "The full documentation is available here: `https://liualgotrader.rtfd.io`."
    )
    if restore_sample_db:
        print()
        print(
            "The restored database includes data for the first week and half of Oct 2020."
        )
        print(
            "You may now run a back-testing sessions for these days, as well as "
        )
        print("analyze an existing trading session.")
    print()

    if sample_location:
        print("To experience Liu Algo Trading for the first time:")
        print(
            f"1. change your working directory to the sample directory {sample_location} ('cd {sample_location}'),"
        )
        if os.name == "nt":
            print("2. run the env-vars script ('env_vars.bat'),")
        else:
            print("2. run the env-vars script ('source env_vars.sh'),")
        print(
            "3.`streamlit run https://raw.github.com/amor71/LiuAlgoTrader/master/analysis/backtester_ui.py`"
        )
        if restore_sample_db:
            print("4. On the app selection select the 'analyzer` app")
            print(
                "5. copy and paste the batch-id '2398380c-5146-4b58-843a-a50c458c8071' and press <enter>"
            )

    print()
    print("Thank you for choosing Liu Algo Trading Framework. ")
    print()


def create_account(amount: float, credit: float):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_db_connection())
    account_id = loop.run_until_complete(
        Accounts.create(amount, allow_negative=credit > 0, credit_line=credit)
    )
    print(f"Account ID {account_id} created")


def create_portfolio(amount: float, credit: float):
    portfolio_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_db_connection())
    loop.run_until_complete(
        Portfolio.save(
            portfolio_id=portfolio_id,
            portfolio_size=amount,
            credit=credit,
            parameters={},
        )
    )
    print(f"Portfolio ID {portfolio_id} created")


def main_cli() -> None:
    config.filename = os.path.basename(__file__)

    try:
        config.build_label = pygit2.Repository("../").describe(
            describe_strategy=pygit2.GIT_DESCRIBE_TAGS
        )
    except pygit2.GitError:
        import liualgotrader

        config.build_label = liualgotrader.__version__ if hasattr(liualgotrader, "__version__") else ""  # type: ignore

    if len(sys.argv) < 2:
        show_usage()
        exit(0)

    if sys.argv[1] == "quickstart":
        try:
            quickstart()
        except KeyboardInterrupt:
            print("Oops... exiting gracefully")
    elif sys.argv[1] == "create":
        try:
            if sys.argv[2] == "portfolio":
                if float(sys.argv[3]) <= 0.0:
                    print(
                        "Oops.. account size must be positive. Always think positive w/ Liu"
                    )
                    exit(0)
                amount = float(sys.argv[3])

                credit = 0.0
                opts, args = getopt.getopt(
                    sys.argv[4:],
                    shortopts="",
                    longopts=[
                        "credit=",
                    ],
                )
                for opt, arg in opts:
                    if opt in ("--credit"):
                        credit = float(arg)
                        if credit <= 0.0:
                            print(
                                "Oops.. creditamount must be positive. Always think positive w/ Liu"
                            )
                            exit(0)

                create_portfolio(amount, credit)
        except Exception as e:
            print(f"[ERROR] {e}")
            show_usage()
    else:
        show_usage()

    exit(0)


main_cli()