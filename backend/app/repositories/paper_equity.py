from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from trading.broker.paper_broker import PaperBroker

from app.db.models import PaperEquitySnapshotRecord


class PaperEquityRepository:
    """Persist deduplicated account equity observations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        event_id: str,
        broker: PaperBroker,
        *,
        captured_at: datetime,
        commit: bool = True,
    ) -> None:
        if captured_at.tzinfo is None:
            raise ValueError("equity snapshot timestamp must be timezone-aware")
        statement = insert(PaperEquitySnapshotRecord).values(
            event_id=event_id,
            captured_at=captured_at.astimezone(UTC),
            equity=broker.equity,
            exposure=broker.current_exposure,
            realized_pnl=broker.realized_pnl,
            unrealized_pnl=broker.unrealized_pnl,
        )
        await self.session.execute(statement.on_conflict_do_nothing())
        if commit:
            await self.session.commit()

    async def list_all(self) -> list[dict[str, float | datetime]]:
        result = await self.session.execute(
            select(PaperEquitySnapshotRecord).order_by(
                PaperEquitySnapshotRecord.captured_at,
                PaperEquitySnapshotRecord.event_id,
            )
        )
        snapshots = []
        for record in result.scalars():
            captured_at = record.captured_at
            if captured_at.tzinfo is None:
                captured_at = captured_at.replace(tzinfo=UTC)
            snapshots.append(
                {
                    "event_id": record.event_id,
                    "captured_at": captured_at,
                    "equity": record.equity,
                    "exposure": record.exposure,
                    "realized_pnl": record.realized_pnl,
                    "unrealized_pnl": record.unrealized_pnl,
                }
            )
        return snapshots

    async def list_history(self) -> list[dict[str, float | datetime | str]]:
        snapshots = await self.list_all()
        baseline = [item for item in snapshots if item["event_id"] == "paper-account-baseline"]
        daily: dict[object, dict[str, float | datetime | str]] = {}
        for snapshot in snapshots:
            if snapshot["event_id"] == "paper-account-baseline":
                continue
            day = snapshot["captured_at"].date()  # type: ignore[union-attr]
            current = daily.get(day)
            if current is None or snapshot["captured_at"] > current["captured_at"]:
                daily[day] = snapshot
        return sorted([*baseline, *daily.values()], key=lambda item: item["captured_at"])

    @staticmethod
    def cache_daily_snapshot(
        history: list[dict[str, float | datetime | str]],
        event_id: str,
        broker: PaperBroker,
        *,
        captured_at: datetime,
    ) -> list[dict[str, float | datetime | str]]:
        if captured_at.tzinfo is None:
            raise ValueError("equity snapshot timestamp must be timezone-aware")
        captured_at = captured_at.astimezone(UTC)
        snapshot: dict[str, float | datetime | str] = {
            "event_id": event_id,
            "captured_at": captured_at,
            "equity": broker.equity,
            "exposure": broker.current_exposure,
            "realized_pnl": broker.realized_pnl,
            "unrealized_pnl": broker.unrealized_pnl,
        }
        if event_id == "paper-account-baseline":
            if not any(item["event_id"] == event_id for item in history):
                history.append(snapshot)
        else:
            daily = [
                item
                for item in history
                if item["event_id"] != "paper-account-baseline"
                and item["captured_at"].date() == captured_at.date()  # type: ignore[union-attr]
            ]
            latest = max(daily, key=lambda item: item["captured_at"]) if daily else None
            if latest is None or captured_at >= latest["captured_at"]:
                history = [item for item in history if item not in daily]
                history.append(snapshot)
        return sorted(history, key=lambda item: item["captured_at"])
