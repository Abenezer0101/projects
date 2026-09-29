# SQLite under concurrent writers

Eight processes, each opening its own connection to one database file and
committing 300 single-row transactions. Rollback journal against WAL, with the
errors counted rather than described.

```
python3 lab.py        # ~8 seconds
```

Processes, not threads: a thread pool shares one interpreter and hides the
contention this is about.

## Result

| journal | busy_timeout | seconds | written | lost to lock | writes/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| delete | 0ms | 0.06 | 22 | 2378 | 378 |
| delete | 5000ms | 2.64 | 2400 | 0 | 910 |
| wal | 0ms | 0.06 | 95 | 2305 | 1666 |
| wal | 5000ms | 0.90 | 2400 | 0 | 2658 |

The exact failure is `sqlite3.OperationalError: database is locked`.

With no busy timeout, both modes throw away roughly 95% of the work — the
surviving count swings between about 20 and 280 across runs, because it
depends on which process happens to win each race, but the loss is total
enough that the exact figure is not the point. WAL does not rescue you here.
It is not a concurrency mode, it is a journalling mode.

With a five-second busy timeout, nothing is lost in either mode and WAL
finishes 2.9× faster. That is the whole practical difference for writes.

Python's `sqlite3.connect()` already defaults `timeout` to 5.0 seconds, so the
0ms row is something you have to opt into — but it is exactly what you get by
setting `PRAGMA busy_timeout=0`, or by using a driver in another language that
does not set one. The C library's own default is 0.

## WAL does not give you concurrent writers

It is described that way constantly. Same 2400 writes, spread over more
processes:

| writers | seconds | writes/s |
| ---: | ---: | ---: |
| 1 | 0.57 | 4191 |
| 2 | 0.66 | 3618 |
| 4 | 0.85 | 2837 |
| 8 | 0.90 | 2663 |

Throughput does not rise. It *falls*, by 1.6× from one writer to eight. One
writer holds the write lock at a time in WAL exactly as in rollback journal;
adding writers adds queueing, and the queueing is not free.

## What WAL actually buys

```
reader holding an open transaction, second connection tries to write:
  delete  -> writer blocked: OperationalError: database is locked
  wal     -> writer succeeded while a reader held a transaction
```

That is the real difference. In rollback-journal mode a reader with an open
transaction blocks every writer for as long as it holds it — one slow report
query stalls all writes. In WAL the writer appends to the log and the reader
keeps its snapshot. Readers and writers stop fighting; writers still fight
each other.

## A bug worth keeping

The first version of this script reported 172 successful writes while 262 rows
were sitting in the table. A commit that raises `database is locked` leaves
the transaction **open**, so the pending row is still there and the next
successful commit sweeps it in. The error count and the row count disagreed,
and only an assertion comparing them caught it.

The fix is the `con.rollback()` in the exception handler, so a write counted
as lost is actually lost. The assertion is still in `run()`:

```python
assert stored == ok, f"counted {ok} successes but {stored} rows landed"
```

Any benchmark that counts failures without rolling back is measuring
something other than what it says.
