"""Seed the development database with a realistic, feature-covering dataset.

Drives the real use cases (never raw SQL), so every row respects the same
invariants the app enforces. The result exercises each screen/feature at least
once: a multi-copy catalog across material types, patrons in every category
plus a suspended and an expired one, active / overdue / renewed / audiovisual
loans, a ready hold on the shelf with a pending queue behind it, a cancelled
hold, and items in repair / lost / withdrawn states.

Run from the ``backend/`` directory (the SQLite URL is relative to cwd)::

    uv run python scripts/seed.py            # seed an empty DB
    uv run python scripts/seed.py --reset    # delete library.db first, then seed

Idempotency: refuses to run against a non-empty DB unless ``--reset`` is given,
so re-running never produces duplicate-barcode errors.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Make ``app`` importable when invoked as ``python scripts/seed.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.application.use_cases.catalog import (  # noqa: E402
    AddItem,
    CatalogManifestation,
    ChangeItemState,
    CreateWork,
)
from app.application.use_cases.circulation import (  # noqa: E402
    CancelHold,
    CheckIn,
    CheckOut,
    PlaceHold,
    RenewLoan,
)
from app.application.use_cases.patrons import (  # noqa: E402
    RegisterPatron,
    SuspendPatron,
)
from app.infrastructure.config import Settings  # noqa: E402
from app.infrastructure.db.engine import (  # noqa: E402
    make_engine,
    make_session_factory,
)
from app.infrastructure.db.migrations import upgrade_to_head  # noqa: E402
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork  # noqa: E402
from app.infrastructure.policy_provider import (  # noqa: E402
    StaticLoanPolicyProvider,
)
from app.domain.value_objects import (  # noqa: E402
    ItemState,
    MaterialType,
    PatronCategory,
)

PICKUP_WINDOW_DAYS = 7


class SeedClock:
    """Adjustable Clock: lets the seed back-date a checkout to forge an overdue
    loan, then snap back to ``today`` for everything else."""

    def __init__(self, today: date) -> None:
        self._today = today

    def set_today(self, day: date) -> None:
        self._today = day

    def now(self) -> datetime:
        return datetime(self._today.year, self._today.month, self._today.day, 12)

    def today(self) -> date:
        return self._today


def _sqlite_path(database_url: str) -> Path | None:
    """The on-disk file for a ``sqlite:///relative`` or ``sqlite:////abs`` URL."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    return Path(database_url[len(prefix):])


def _db_has_data(session_factory) -> bool:
    uow = SqlAlchemyUnitOfWork(session_factory)
    with uow:
        return uow.works.get(1) is not None


def log(msg: str) -> None:
    print(f"  {msg}")


def seed(session_factory, today: date) -> None:
    clock = SeedClock(today)
    policy = StaticLoanPolicyProvider()
    uow = SqlAlchemyUnitOfWork(session_factory)

    create_work = CreateWork(uow)
    catalog_manifestation = CatalogManifestation(uow)
    add_item = AddItem(uow)
    change_item_state = ChangeItemState(uow)
    register_patron = RegisterPatron(uow)
    suspend_patron = SuspendPatron(uow)
    check_out = CheckOut(uow, policy, clock)
    check_in = CheckIn(uow, clock, PICKUP_WINDOW_DAYS)
    renew_loan = RenewLoan(uow, policy, clock)
    place_hold = PlaceHold(uow, clock)
    cancel_hold = CancelHold(uow, clock, PICKUP_WINDOW_DAYS)

    # --- Patrons ------------------------------------------------------------
    print("Patrons:")
    register_patron.execute("C001", PatronCategory.general)
    register_patron.execute("C002", PatronCategory.student)
    register_patron.execute("C003", PatronCategory.child)
    register_patron.execute("C004", PatronCategory.general)
    suspend_patron.execute("C004")
    register_patron.execute(
        "C005", PatronCategory.general, expires_on=today - timedelta(days=1)
    )
    log("C001 general, C002 student, C003 child (all active)")
    log("C004 general — suspended; C005 general — card expired yesterday")

    # --- Catalog: Work -> Manifestation -> Item(s) --------------------------
    print("Catalog:")

    def book(title: str, author: str, *barcodes: str, isbn: str | None = None):
        work = create_work.execute(title, author)
        man = catalog_manifestation.execute(
            work_id=work.id, title=title,
            material_type=MaterialType.book, isbn=isbn,
        )
        for bc in barcodes:
            add_item.execute(man.id, bc)
        return man

    kokoro = book("Kokoro", "Natsume Soseki", "B001", "B002", isbn="9784101010137")
    norwegian = book("Norwegian Wood", "Haruki Murakami", "B003")
    snow = book("Snow Country", "Yasunari Kawabata", "B004")
    sheep = book("A Wild Sheep Chase", "Haruki Murakami", "B007", "B008")
    botchan = book("Botchan", "Natsume Soseki", "B009")
    rashomon = book("Rashomon", "Ryunosuke Akutagawa", "B010")

    genji_work = create_work.execute("The Tale of Genji", "Murasaki Shikibu")
    genji = catalog_manifestation.execute(
        work_id=genji_work.id, title="The Tale of Genji (annotated reference)",
        material_type=MaterialType.reference,
    )
    add_item.execute(genji.id, "B005")

    spirited_work = create_work.execute("Spirited Away", "Hayao Miyazaki")
    spirited = catalog_manifestation.execute(
        work_id=spirited_work.id, title="Spirited Away (DVD)",
        material_type=MaterialType.audiovisual,
    )
    add_item.execute(spirited.id, "B006")
    log("8 works across book / reference / audiovisual; 10 physical copies")

    # --- Loans --------------------------------------------------------------
    print("Loans:")
    check_out.execute("B001", "C001")  # plain active book loan
    log("C001 has B001 on loan (active, due in 14d)")

    check_out.execute("B006", "C001")  # audiovisual, shorter period
    log("C001 has B006 (DVD) on loan (active, due in 7d)")

    check_out.execute("B004", "C003")  # then renewed below
    renew_loan.execute("B004")
    log("C003 has B004 on loan, renewed once")

    # Overdue: back-date the checkout so the due date is already in the past.
    clock.set_today(today - timedelta(days=40))
    check_out.execute("B003", "C002")
    clock.set_today(today)
    log("C002 has B003 on loan — OVERDUE (borrowed 40d ago; blocks new borrows)")

    # --- Holds --------------------------------------------------------------
    print("Holds:")
    # Put both copies of 'A Wild Sheep Chase' out, then queue two patrons and
    # return one copy so the head's hold goes onto the ready shelf.
    check_out.execute("B007", "C001")
    check_out.execute("B008", "C001")
    place_hold.execute(sheep.id, "C002")  # queue head
    place_hold.execute(sheep.id, "C003")  # waiting behind
    check_in.execute("B007")  # fulfills C002's hold -> ready on the shelf
    log("'A Wild Sheep Chase': C002 hold READY on shelf, C003 pending behind")

    # A cancelled hold (Snow Country's only copy is out on C003's renewed loan).
    cancellable = place_hold.execute(snow.id, "C001")
    cancel_hold.execute(cancellable.hold_id)
    log("C001 placed then cancelled a hold on 'Snow Country'")

    # --- Item states --------------------------------------------------------
    print("Item states:")
    change_item_state.execute("B002", ItemState.in_repair)
    change_item_state.execute("B009", ItemState.lost)
    change_item_state.execute("B010", ItemState.withdrawn)
    log("B002 in_repair, B009 lost, B010 withdrawn")

    # Reference unused so far in loans on purpose: keep the reference copy and
    # the suspended/expired patrons available to demo the blocking error paths.
    _ = (kokoro, norwegian, botchan, rashomon, genji)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true",
        help="delete the existing SQLite file before seeding",
    )
    args = parser.parse_args()

    settings = Settings()
    db_url = settings.database_url
    db_path = _sqlite_path(db_url)

    if args.reset and db_path is not None and db_path.exists():
        db_path.unlink()
        print(f"Deleted {db_path}")

    upgrade_to_head(db_url)
    engine = make_engine(db_url)
    session_factory = make_session_factory(engine)

    if _db_has_data(session_factory):
        print(
            "Database already contains data. Re-run with --reset to rebuild it "
            "from scratch.",
            file=sys.stderr,
        )
        return 1

    today = date.today()
    print(f"Seeding {db_url} (today = {today})\n")
    seed(session_factory, today)
    print("\nDone. Start the app and explore the seeded data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
