import asyncio
from pathlib import Path

import aiosqlite

from saga.models.torrent import ResolvedTorrent


async def _init_db(db: aiosqlite.Connection) -> None:
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS torrents (
            info_hash TEXT PRIMARY KEY,
            data TEXT NOT NULL
        );
    """)


class TorrentDatabaseRepo:
    def __init__(
        self,
        path: Path | str,
    ):
        self._path: str = str(path)
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is not None:
            return self._db

        async with self._lock:
            if self._db is not None:
                return self._db

            target_path: Path | str = self._path
            if self._path != ":memory:":
                resolved_path = Path(self._path).resolve()
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
                target_path = resolved_path

            self._db = await aiosqlite.connect(target_path)
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA journal_mode = WAL;")
            await _init_db(self._db)

            return self._db

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def insert_torrent(self, torrent: ResolvedTorrent):
        db = await self._get_db()
        await db.execute(
            "INSERT INTO torrents (info_hash, data) VALUES (?, ?)",
            (torrent.info_hash, torrent.model_dump_json()),
        )
        await db.commit()

    async def get_torrent(self, info_hash: str) -> ResolvedTorrent | None:
        db = await self._get_db()
        cur = await db.execute(
            "SELECT data FROM torrents WHERE info_hash = ? LIMIT 1", (info_hash,)
        )
        row = await cur.fetchone()
        if row:
            return ResolvedTorrent.model_validate_json(row["data"])
