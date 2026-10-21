# What porting Arvo says about Jock

Written while building `juno`. Each item is something that
actually cost something here, not a wishlist. Ordered by what it
cost.

## 1. No functional record update

The big one.

Hoon's whole idiom for a state machine is the mutation form:
`..poke(sol q.p.zef)`, `this(run [pan run])`,
`..pith(lac.fad ?~(p.waif !lac.fad u.p.waif))`. Arvo's event loop
is *built* out of it — `+emit` is one such update, `+step` is a
`?-` whose every branch is another, and the kernel arms end by
rebuilding themselves around one changed field.

Jock has no equivalent. To change one field of a struct you
respell every field:

```jock
match dill.call(v.d, duct, task) {
  (mz, d2) => (mz, Vanes( d: d2, e: v.e )),
}
```

Two structural concessions in this port come from that and
nothing else:

- the vane states were split into their own `Vanes` struct so the
  loop would not respell the kernel's scalar fields (`now`, `our`,
  `eny`, `lac`) at every step;
- `+vcall` and `+vtake` exist partly to confine the respelling to
  two sites instead of six.

Both are defensible as design, which is what makes this worth
flagging: the workaround is invisible in the result. Scale it to a
real Arvo — seven state fields, ten vanes — and every state write
is a ten-field literal whose correctness is a reader's eyeball
over ten `x: s.x` pairs. That is where a transcription bug lives.

Not in `docs/spec/language.md`, not in `docs/POSSIBLES.md`, so
this appears to be unrecorded rather than deferred.

## 2. Recursive enums cannot be declared

Arvo's `$ball` is `(wite [vane task] maze)` and `$wite`'s `%hurl`
case carries **another** `$wite`. Jock cannot declare that, so
juno models the error as a field of the move
(`struct Move { duct, ball, dud: Goof? }`) and drops `%hurl` from
the enum.

That substitution is sound here — `%hurl`'s entire effect in
`+step` is "set `.dud` and re-step the inner ball", which is
exactly one level of nesting — and it reads flatter than the
original. But it was a judgement call forced by the language, and
the next recursive type may not have an equivalent flattening.

`crates/jockc/hoon/lib/chaintx.jock:188` already records this wall
for the chain work ("recursive untagged union cannot be declared
from source at all"). juno is a second, independent customer,
which makes it a pattern rather than a one-off.

## 3. Mutual recursion is positional, and fails silently

`+vcall`, `+vtake`, `+step` and `+drain` are mutually recursive.
That requires them to be **textually contiguous** `func`s: a run
of adjacent `func` declarations is made mutually visible, and any
interposed declaration splits the run, after which the forward
call is a bare `%mint-limb` with no explanation.

So the loop in `juno.jock` is one block fenced by a comment asking
the reader not to insert anything into it. Nothing in the language
expresses the constraint, and nothing in the error points at it.

`docs/spec/language.md:269` promises a *"move these `func`s
together"* hint; `grep` finds no such string in `mint.hoon`, so
the diagnostic the spec describes does not exist.

## 4. Inference does not flow into a call

`cons` is `func<T> cons(x: T, xs: List<T>) -> List<T>`. Writing a
one-element wire as

```jock
wire: cons(%say, ~)
```

is refused `%mill-nest`. The term literal `%say` has a singleton
type, that solves `T`, and the resulting `List<%say>` does not
nest into the `List<@>` the field wants. Nothing is wrong with
either half — it is that no expected type flows from the field
into the call to pin `T` at `@`.

The fix is to drop the constructor and let the field do the work:

```jock
wire: (%say, ~)
```

A bare cons cell in **field position** nests directly, because
assignment nests rather than joins. So the workaround is shorter
than the thing that failed, which is the confusing part: `cons`
is the prelude's blessed list constructor, and here using it is
what breaks.

This is the same shape as the note in the chain work that a
numeric literal passed to `cons` needs `(x as! Char)` to pin `T`
against a `List<Char>` tail. Two independent customers for
checking-position propagation.

## 5. `parse.hoon`'s own precedence table is stale

Not a language gap — a documentation bug, in the compiler.

`crates/jockc/hoon/lib/parse.hoon:14` and `:34` both list a
postfix **`struct-literal {`** at precedence level 2. There is no
such form: `+p-post` accepts a glued `(` (call / struct literal),
a glued `[` (index) and `.` (field), and nothing else.
`docs/spec/language.md:5` records that the syntax arc "moved
construction to the glued paren", which is what actually happened.

A reader trusting the compiler's own table writes `St( n: 0 )` for
a statement and `St{ n: 0 }` inside a tuple, and the second gets
`%parse-expected %')'` pointing at the brace. Cost here: one build
cycle, which is not cheap (see 8).

## 6. `loop` is a keyword

Arvo's move-loop arm is called `+loop`. Jock reserves `loop` for
the `loop`/`recur` construct, so the port calls it `+drain` and
carries a comment saying why. Cosmetic, except that the one name
the domain wants is the one that is taken.

## 7. No empty-term literal

Arvo spells its pseudo-vane `%$` — the sentinel meaning "Arvo
itself" inbound and "the runtime" outbound. It is the atom `0`,
but it *reads* as a term, and it is load-bearing vocabulary in the
thing being ported.

Jock has no `%$`, so juno defines `func outside() -> @ { 0 }` and
calls that. Workable; the comparison `if way == lull.outside()`
reads less directly than `?: =(%$ way)`.

## 8. Compile time governs the development loop

A 340-line program across three modules takes about four minutes
to build, and a one-character syntax error costs the whole build
before it reports. Evaluating the emitted trap costs that again,
because kicking it *is* running the compiler — which is also why
the test harness takes an already-evaluated core rather than the
trap `build.sh` produces. That turns ordinary syntax uncertainty — *is it `{` or
`(`?* — into an expensive question, which is why item 5 mattered
enough to write down.

Nothing here is wrong, and a compiler written in Hoon running
under `honk` is not going to be fast. But it changes how one
writes Jock: you read the compiler source to settle syntax
questions rather than trying them, which is only possible because
the compiler source happens to be at hand.

## 9. No ambient context for a callee

Arvo `+spin`s a vane with `[duct eny dud]` so that the vane's own
arms stay narrow and the context is implicit. Jock has nothing
like it, so every vane arm carries the context explicitly:
`call(s, duct, task)`, `take(s, duct, wire, sign)`.

This is probably the *right* trade — the dependency is visible in
the signature, and Arvo's implicit spin is the kind of thing that
makes a vane hard to test in isolation. It is listed because it
compounds with item 1: wide arms plus no record update is what
makes the loop's plumbing the bulk of its text.

---

# What worked, and is worth saying

Balance matters here, because the list above is what a port
notices and is not the whole picture.

- **Module-imports-module, including types.** `lull.Duct` appears
  in a vane's signature and a vane's `St` appears in the kernel's
  state struct. The three-layer split — vocabulary, vanes, kernel
  — is only possible because a module can build on another
  module's types, which is recent. Without it this would have
  been one file.
- **`enum` with payload cases is exactly `$ball`.** `.pass(p) =>`
  destructuring a tagged case is a direct transcription of
  Arvo's `?-  -.ball.move`, with exhaustiveness checked.
- **`T?` needed no unit combinators.** `dud: Goof?` and
  `match d2 { ~ => …, _ => … }` is the whole of it.
- **The mirror-struct-plus-`as!` idiom reads the event cleanly.**
  There is no axis arithmetic anywhere in this port: the runtime
  hands over `[now wire mark data]` and a four-field struct names
  it.
- **The ABI was free.** `+kbatt` already lands its arms on Arvo's
  axes `+4`/`+10`/`+22`/`+23`, and the poke already takes
  `[now ovo]` and returns `[fx kernel']`. That is the difference
  between this being an exercise and being a compiler project.
