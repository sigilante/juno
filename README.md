# juno — the Arvo event loop, in Jock

Arvo is an event processor with a four-arm outer interface at four
fixed axes. juno is that interface and that event loop, written in
[Jock](https://github.com/sigilante/jock) instead of Hoon.

## The ABI was already Arvo-shaped

Jock's kernel adapter (`+kbatt`, `crates/jockc/hoon/lib/jock.hoon`)
emits a battery of `[load 0 peek poke]`. Read as a core's battery,
that puts the arms at:

| axis | arm | Arvo |
|------|-----|------|
| `+4`  | load | `+load`, state migration |
| `+10` | — (atom `0`) | `+wish`, parse-against-`%zuse` |
| `+22` | peek | `+peek`, scry |
| `+23` | poke | `+poke`, event application |

Those are Arvo's axes, exactly, and this is not a coincidence that
has to be arranged — it is what the adapter already does, because
NockApp's kernel ABI was modelled on Arvo's. `tools/test.py` reads
the arms off those axes and fires `+23` with Arvo's own sample,
`[now ovo]`, and gets back Arvo's own product, `[fx kernel']`,
where the rebuilt kernel answers all four arms and the state has
advanced. Nothing in the harness knows anything about Jock.

So the interesting work is not the interface. It is the semantics:
the move loop, and the question of what a statically-typed
compiled language does and does not need from Arvo's design.

## What the vase layer was for, and what happens without it

Arvo's `$card` is a `(cask)`: `[mark=@tas vase]`.

The **mark** ports to Jock unchanged. It is wire-format data —
it names a payload's shape for a peer that may be a different ship
running different code — and no amount of static typing removes
the need for it.

The **vase** does not port, and does not need to. Arvo pairs every
payload with a Hoon `$type` because a vane is a `vase` and calling
one is a `+slap`: the caller's type is not known to the callee at
compile time, so it travels with the value. A juno vane is a gate
with a static signature, so that type is discharged when the
kernel is compiled and the runtime carries the noun alone.

Deleting the vase deletes `$maze`, `$meta`, `+hypo`, `$vile`,
`+viol`, `$worm`, `+wa`, `+refine-moves`, and every `+slap` and
`+slop` with them. It also deletes three fields of Arvo's
persistent state: `pit` (the compiled type cache), `vil`, and
`bud` (`%zuse` itself). juno's state is `[now our eny lac vanes]`,
and what is left is the part that was never about types.

This is the one real claim of the exercise: **a large fraction of
Arvo's internal machinery is the cost of carrying Hoon's types
through a dynamically-assembled kernel, and a compiled language
does not pay it.**

## What ports faithfully

The loop is Arvo's loop, arm for arm:

- `$move` is `[duct ball]`; `$duct` is a list of wires, most
  recent frame first; `$ball` is `%pass`/`%give`/`%slip`.
- **`%pass`** conses the source vane onto the wire, then the wire
  onto the duct. That is the whole of Arvo's causal bookkeeping.
- **`%give`** pops the duct. The popped wire's head names the
  target and its tail is the wire handed back to it; the source
  vane is consed onto the gift to make a `$sign`.
- **`%slip`** leaves the duct alone, so the callee's eventual
  `%give` returns to the original caller.
- **`%$`** is the pseudo-vane: Arvo itself on the way in, the
  runtime on the way out. A `%give` to `%$` is only legal at the
  bottom of the duct, and becomes an ovum.
- an incoming ovum routes by its **wire head** (Arvo's `+gest`).
- `.run` is a stack of worklists and `.out` accumulates reversed,
  as `+abet` flops it.
- ordering is **depth-first**, as Arvo's is today. Arvo intends to
  switch to breadth-first; here that is one word — append instead
  of cons, at the three sites in `+step`.

Two deliberate deviations, both noted at their definitions:

- **`%hurl` is a field, not a ball case.** Arvo's `$ball` is
  recursive (`%hurl` carries another ball) and Jock cannot declare
  a recursive enum. It does not need to: `%hurl`'s entire effect
  in `+step` is "set `.dud` and re-step the inner ball", so
  carrying the goof as a field of the move is equivalent at the
  one level of nesting Arvo ever produces.
- **`$goof`'s tang is rendered text.** A `$tang` is a
  `(list tank)` and a tank is pretty-printer input — a Hoon value,
  not a noun shape.

## What is not here, and why

Three different reasons, kept apart on purpose:

**Impossible without a Hoon compiler in the kernel.**
`+wish` *is* "run the Hoon compiler", so axis `+10` is the atom
`0`. A caller gets a crash rather than a wrong answer. Likewise
`%veer`-style runtime vane installation: Arvo can install a vane
at runtime because a vane is a vase, i.e. data. A juno vane is
code, so the vane table is a static dispatch and the set of vanes
is fixed when the kernel is built. This is the sharpest trade in
the port and it is a real loss, not a simplification.

**Possible but unbuilt.** Kernel version negotiation (`%wyrd`,
`$wynn`), OTA and the `+what` update engine, Arvo's own self-tasks
(`%trim`/`%verb`/`%whey`), vane `+scry` threading, and a versioned
state union for `+load` (the draft grafts same-shape).

**Deliberately different.** Arvo `+spin`s each vane with
`[duct eny dud]` as ambient context; juno passes what a vane needs
as explicit parameters, which is why the vane arms are wide.

## Layout

    pkg/juno/sys/juno.jock        the kernel: four arms, the move loop
    pkg/juno/sys/lib/lull.jock    the vocabulary vanes and kernel share
    pkg/juno/sys/vane/dill.jock   %d, a vane that gives
    pkg/juno/sys/vane/echo.jock   %e, a vane that passes and takes
    tools/build.sh                -> out/juno.jam
    tools/test.py                 drive it through Arvo's interface

`%d` and `%e` are there to drive the loop, not to be useful. `%d`
takes a task and gives, which reaches `+call` and the `%give` leg.
`%e` passes to `%d` and then takes its answer, which is the only
path that grows the duct past one frame and the only one that
reaches `+take`. Between them one event exercises every mechanism
in `+step` except `%slip`.

## Build and run

    JOCK=~/Code/jock zsh tools/build.sh          # -> out/juno.jam
    honk-kick out/juno.jam out/juno-core.jam     # evaluate the trap
    python3 tools/test.py out/juno-core.jam

`build.sh` emits a bootable *trap*; kicking it is what produces
the kernel core. Kick it with `honk-kick` rather than in Python —
evaluating the trap means running the Jock compiler, and a
pure-Python Nock does not finish that.

## Two calling conventions, and which one juno satisfies

Arvo is called two different ways, and juno currently answers one
of them.

**A practical interpreter** — Vere's serf — fires `+poke` at axis
`+23` directly. juno satisfies this today, and `tools/test.py`
exercises exactly it.

**The formal lifecycle** — `+aeon:eden:part`, the first event in a
ship's log — does not. It treats the kernel state as a *gate* and
fires `.*([arvo ovo] [%9 2 %10 [6 %0 3] %0 2])`: arm **2**, with
the sample edited in. That is why Arvo ends with a wrapper,

    |=  [now=@da ovo=ovum]
    ^-  *
    .(+> +:(poke now ovo))

whose only job is to make a multi-armed core look like a
one-armed gate. Arvo's own comment on it reads "a practical
interpreter can and will ignore it", and that is the whole
difference: juno is a four-arm core with no wrapper, so `[9 2 …]`
against it addresses the battery rather than a formula.

So booting juno from a pill needs the wrapper, and being poked by
a running serf does not. Emitting the wrapper is a change to
jock's `+kbatt` (or a trap around its product), not to anything in
this repository — which is the concrete next step, and is a
smaller question than the larval stage, which juno does not model
at all.

## Status

A draft. The ABI claim is measured rather than asserted, and
`tools/test.py` drives the loop end to end over both a one-frame
and a two-frame duct, checking the duct discipline by its
observable consequences: which vane ran, how deep the duct got,
and what reached the runtime.

The duct discipline is pinned by mutation, not just exercised:
making `%pass` cons `%$` instead of the real source leaves the
short path **entirely green** -- that path's source genuinely is
`%$`, so the mutation is inert there -- and crashes the long path
on the empty-duct assert in `%give`. So the long path depends on
the source-cons rather than passing for some other reason, which
is the only thing a green loop test can be worth.

Two soft spots, both deliberate and neither hidden in the code:

- **`%slip` is written but unexercised.** Neither vane slips, so
  that case of `+step` is reachable by no test. It is present
  because the loop is not faithful without it, and it is
  currently the one case resting on reading rather than running.
- **`+peek` is shallower than Arvo's.** Arvo's takes
  `[lyc=gang nom=…]` and threads into each vane's `+scry`; this
  one answers kernel state only. The harness uses it as an
  observation port, which is honest, but it means peek is tested
  as an instrument rather than as the arm Vere would call.

It has never been booted by Vere. See above for what that would
take.

See `DEFICIENCIES.md` for what writing it says about Jock.
