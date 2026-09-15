# Focus Timer

A Pomodoro timer whose interesting part is not the countdown — it is refusing to
count.

**[Open it →](https://abenezer0101.github.io/projects/focus-timer/)**

## Why a timer is not a for-loop

The obvious implementation counts ticks:

```js
setInterval(() => { left -= 1000; render(); }, 1000);   // wrong
```

`setInterval` does not promise 1000ms. It promises *not sooner than* 1000ms.
Browsers clamp hidden tabs to roughly one fire per minute, and a suspended tab
may not fire at all. A tick-counter treats every fire as exactly one second no
matter how long it really was, so a timer backgrounded for two minutes comes
back believing two **seconds** passed.

Everything here derives elapsed time from wall-clock timestamps instead. A
session stores *when it started*, never *how much is left*, and a repaint is
only a prompt to re-read the clock.

## The cost, measured

Both implementations are fed the identical sequence of timer fires, simulating a
browser that runs 4ms late per fire and clamps to one per minute while hidden.
Over a single 25-minute block:

| Situation | Tick-counter thinks | Wall clock knows | Lost |
| --- | --- | --- | --- |
| Foreground the whole time | 1495s | 1500s | **5s** |
| 2 minutes backgrounded | 1377s | 1500s | **123s** |
| 10 minutes backgrounded | 907s | 1500s | **593s** |

Even undisturbed in the foreground it loses five seconds a block. Ten minutes in
a background tab and a "25-minute" block runs for nearly 35. The failure is
silent — the countdown looks perfectly normal the whole time, which is what
makes it worth engineering around. `tickCounter` and `clockReader` in
`timer.js` are both exported so the comparison is reproducible, and the
browser tests assert the shipped timer keeps real time across a hidden tab.

## A bug the tests missed

`nextPhase` awards a long break every 4th focus block: `completed % 4 === 0`.
That is true when `completed` is **0**, so abandoning your very first block
earned a 15-minute long break. The unit tests checked 1, 2, 3, 4 and 8 — every
case except the one that happens before you have done anything. It took a
screenshot showing **LONG BREAK** immediately after the first skip to see it.

## Session stats

Everything in the panel is computed from the log of finished sessions; nothing
is stored pre-computed.

- Total focus time, counting only **completed** blocks, with abandoned time
  reported separately rather than quietly folded in
- Completion rate — blocks finished over blocks started
- Focus by hour of day, so the peak hour is observed rather than assumed
- Current and longest day streak. A streak is only "current" if it reaches
  today or yesterday, so an old run of good days does not masquerade as a live one

## Verification

```
node test_timer.mjs                 # 50 unit tests
node e2e_timer.js /tmp/out          # 26 browser tests (serve the repo on :8095)
```

The state machine takes `now` as a parameter rather than calling `Date.now()`,
so every unit test runs instantly and deterministically — a 25-minute block is
tested in microseconds, and there is nothing to make the suite flaky. The
browser tests check the countdown against real elapsed wall-clock time,
including across a tab marked hidden.
