# Rate limiter, four ways

"100 requests per 60 seconds" sounds like one specification. It is four
different ones, and three of the four implementations here will let a client
exceed it.

```
python3 sweep.py                        # the measurements below
python3 -m unittest discover -q tests   # 22 tests
```

Every limiter takes `now` as an argument instead of calling the clock, so a
ten-minute scenario runs in microseconds and the tests are deterministic. A
limiter that sleeps is a limiter you cannot test.

## The only question that matters

Not "does the counter reset correctly" but: across the whole trace of admitted
requests, what is the most that ever landed in **any** 60-second stretch?
`audit.py` answers that by sliding a window over the admitted timestamps.
Checking aligned windows would let the fixed-window limiter mark its own
homework.

Swept over 119 burst offsets and two attack shapes:

| limiter | worst 60s window | ratio |
| --- | ---: | ---: |
| fixed window | 200 | **2.00×** |
| token bucket | 199 | **1.99×** |
| sliding counter | 101 | 1.01× |
| sliding log | 100 | 1.00× |

## Fixed window: 2× by construction

The counter resets on a clock boundary rather than relative to the requests.
Send 100 at 09:59:59 and 100 at 10:00:00 and both windows are satisfied while
200 requests land in one second. The test pins it:

```python
def test_fixed_window_violates_it(self):
    with self.assertRaises(AssertionError):
        self.assert_holds(FixedWindow(...), boundary_attack())
```

The same assertion that passes for the sliding log is asserted to *raise* for
the fixed window. Lowering the bar until the naive version passes would be the
easy way to make this suite green and would measure nothing.

## Token bucket: 1.99×, and it is not a bug

This one surprised me. A bucket with `capacity == limit` still admits almost
two windows' worth into one rolling window:

```
admitted 199, worst 60s window 199, window starts t=540.5
first admit 540.500, last admit 600.010, span 59.51s
refilled over that span: 99.2 tokens
```

100 from the initially full bucket, plus 99.2 refilled while the client waited
59.5 seconds. A token bucket bounds the long-run **average** rate, not the
rolling maximum — that is the guarantee it offers, and the guarantee people
assume it offers is a different one. If a rolling cap is what you need, a
bucket does not give it to you at any capacity.

## Sliding counter: 1.01×

The two-counter approximation weights the previous window by how far into the
current one you are. That estimate decays continuously, so microseconds after
the boundary it has already dropped below the limit and admits exactly one
extra request. One, not a hundred. Constant memory, 1% error — which is why
it is what production systems usually run.

## Sliding log: exact, and it costs you

Keeping every admitted timestamp and expiring by age makes the invariant
identical to the thing being promised, so there is no boundary to exploit.
The price is memory proportional to the limit, held for a full window, per
client. Exactness is a real cost, not a free win.

## Long-run rate

Hammered at 3× the limit for ten minutes, admitted requests per minute
against a target of 100:

| limiter | per minute |
| --- | ---: |
| token bucket | 109.9 |
| fixed window | 100.0 |
| sliding log | 100.0 |
| sliding counter | 100.0 |

The bucket's +9.9% is its initial full bucket — a one-off 100 amortised over
ten minutes — not a leak. Under sustained load all four converge, which is
exactly why sustained-load testing never finds the boundary bug. The defect
only appears when you go looking for the burst.

## Choosing

Need a hard rolling guarantee, few clients: sliding log. Need it cheap at
scale and 1% over is acceptable: sliding counter. Want to permit bursts on
purpose: token bucket, with `capacity` set deliberately above the limit rather
than by accident. Fixed window: only when 2× the stated limit is genuinely
fine, and then say so in the documentation.
