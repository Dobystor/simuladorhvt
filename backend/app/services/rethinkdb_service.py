"""RethinkDB weight writes for Standard weighing mode.

Writes the user-provided gross weight to the WeighingMachine document before the
HaulageVehicleIntegrationEvent is published, so Haulages.API reads a stable
weight during its stabilisation loop. On any failure the caller aborts the
publish.

Requirements: 9.4, 9.9
"""

from __future__ import annotations

from rethinkdb import RethinkDB


class RethinkDBWriteError(Exception):
    """Raised when the weight write to RethinkDB fails."""


async def write_weighing_machine_weight(
    profile, weighing_machine_rethinkdb_id: str, gross_weight_tonnes: float
) -> None:
    """Update the WeighingMachine document's weight field.

    Uses the asyncio driver. Connects per call and closes afterwards.
    """
    r = RethinkDB()
    r.set_loop_type("asyncio")
    conn = None
    try:
        conn = await r.connect(
            host=profile.rethinkdb.host, port=profile.rethinkdb.port
        )
        await (
            r.table("WeighingMachine")
            .get(weighing_machine_rethinkdb_id)
            .update({"weight": gross_weight_tonnes})
            .run(conn)
        )
    except Exception as exc:  # noqa: BLE001
        raise RethinkDBWriteError(
            f"Failed to write weight to RethinkDB: {exc}"
        )
    finally:
        if conn is not None:
            try:
                await conn.close()
            except Exception:  # noqa: BLE001
                pass
