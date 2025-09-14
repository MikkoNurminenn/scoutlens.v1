from __future__ import annotations

from typing import Sequence

from postgrest.exceptions import APIError


class DeleteError(RuntimeError):
    """Error raised when a delete operation fails."""


def remove_players_from_shortlist(*, client, shortlist_id: str, player_ids: Sequence[str | int]) -> int:
    """Remove players from a shortlist via Supabase.

    Returns the number of deleted rows. Raises :class:`DeleteError` on failure.
    """
    if not player_ids:
        return 0
    try:
        resp = (
            client
            .table("shortlists_items")
            .delete()
            .eq("shortlist_id", shortlist_id)
            .in_("player_id", list(player_ids))
            .select("id")
            .execute()
        )
    except APIError as e:  # pragma: no cover - network errors
        raise DeleteError(f"Shortlist delete failed: {e}") from e
    data = getattr(resp, "data", None)
    return len(data) if isinstance(data, list) else 0


def remove_players_from_storage_by_ids(client, ids: Sequence[str]) -> None:
    """Delete players and related rows in a safe order.

    The function silently ignores missing tables/columns to cope with
    partially migrated databases.
    """

    ids = [i for i in ids if i]
    if not ids:
        return

    try:
        client.table("reports").delete().in_("player_id", ids).execute()
    except APIError:
        pass

    try:
        client.table("shortlist_items").delete().in_("player_id", ids).execute()
    except APIError:
        pass

    client.table("players").delete().in_("id", ids).execute()
