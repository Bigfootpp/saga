from pathlib import Path

import aiosqlite

from saga.models.torrent import ResolvedTorrent


async def _init_db(db: aiosqlite.Connection) -> None:
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS torrents (
            info_hash TEXT PRIMARY KEY,
            data TEXT NOT NULL,
        );
    """)


class TorrentDatabaseRepo:
    def __init__(
        self,
        path: Path | str,
    ):
        self._path: str = str(path)
        self._db: aiosqlite.Connection | None = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db:
            return self._db

        path: Path | str = self._path

        if self._path != ":memory:":
            path = Path(self._path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)

        db = aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode = WAL;")
        await _init_db(db)

        return db

    async def close(self):
        if self._db:
            await self._db.close()

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
            "SELECT data FROM torrents WHERE info_hash = ? LIMIT 1", (info_hash)
        )
        row = await cur.fetchone()
        if row:
            return ResolvedTorrent.model_validate(row["data"])
