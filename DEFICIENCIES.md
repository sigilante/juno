# What porting Arvo says about Jock

Written while building `juno`. Each item is something that
actually cost something here, not a wishlist. Ordered by what it
cost.

Everything below was checked by running it, not by reading the
compiler. Where a claim is about what Jock *cannot* do, the
refusal tag is named.

## 1. Recursive enums cannot be declared

Arvo's `$ball` is `(wite [vane task] maze)` and `$wite`'s `%hurl`
case carries **another** `$wite`. Jock cannot declare that, so
juno models the error as a field of the move
(`struct Move { duct, ball, dud: Goof? }`) and drops `%hurl` from
the enum.

The substitution is sound here — `%hurl`'s entire effect in
`+step` is "set `.dud` and re-step the inner ball", which is
exactly one level of nesting — and it reads flatter than the
original. But it was a judgement call forced by the language, and
the next recursive type may not have an equivalent flattening.

`crates/jockc/hoon/lib/chaintx.jock:188` already records this wall
for the chain work ("recursive untagged union cannot be declared
from source at all"). juno is a second, independent customer,
which makes it a pattern rather than a one-off.

## 2. Mutual recursion is positional, and fails silently

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

## 3. Inference does not flow into a call

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

## 4. `parse.hoon`'s own precedence table is stale

Not a language gap — a documentation bug, in the compiler, about
a spelling the language actively refuses.

`crates/jockc/hoon/lib/parse.hoon:14` and `:34` both list a
postfix **`struct-literal {`** at precedence level 2. There is no
such form, and there is not meant to be: `+p-post` accepts a
glued `(`, a glued `[` and `.` only; `{` in expression position
is a block (`+p-brace`); and the corpus pins the brace spelling as
an **error** — `t-arc-ctor-brace` asserts that
`let p = P{ x: 1 }` refuses `%parse-expected`, paired with
`t-arc-ctor` for the surviving `P(x: 1, y: 2)`.
`docs/spec/language.md:5` records the retirement.

So the compiler's own table documents a form its own test suite
pins as gone. A reader trusting the table writes `St{ n: 0 }` and
gets `%parse-expected %')'` at the brace.

`docs/spec/language.md:105` is loose in the same direction: "An
un-glued `(`, `[`, or `{` is never postfix" implies a *glued* `{`
would be. The table at `:196` is correct and lists no brace.

## 5. Record update is a statement, not an expression

**This item previously claimed Jock had no functional record
update at all. That was wrong, and the error is kept visible here
because it changed the shape of this repository — see below.**

Jock *does* have it. A `var` rebinding plus a field write lowers
to a Nock edit at the field's axis, which is exactly what Hoon's
`s(d d2)` does:

```jock
func bump(s: S) -> S { var t = s; t.b = 99; t };
// bump(S(a: 1, b: 2, c: 3))  ->  (1, (99, 3))
```

It works through a function parameter, through a **nested** path
in one statement (`t.v.d.blits = 7`), and inside a `match` arm,
with sibling fields preserved — all checked by running it.
`+mint`'s `%edit` arm resolves the whole limb path, requires the
binding be mutable (`%mint-edit-immutable` otherwise), and refuses
a write through an imported sealed class with an unusually good
message (`%mint-edit-sealed`: "a class is written only by the
module that declares it; ask it for an arm that rebuilds").

What is actually missing is small: it is a **statement over a
mutable rebinding**, where Hoon's is an inline expression. Hoon
writes `k(v v2)` anywhere a value goes; Jock needs
`{ var t = k; t.v = v2; t }` — three statements, a block, and a
name you have to invent. About two extra lines per update site.

**The cost of getting this wrong was structural.** Believing there
was no record update, this port split the vane states into their
own `Vanes` struct and routed every state write through `+vcall`
and `+vtake`, purely to avoid respelling the kernel's scalar
fields. None of that was necessary. Worse, it reads as design, so
nothing in the result advertises that it is a workaround for a
limitation that does not exist — which is the failure mode worth
recording: a language gap *assumed* rather than tested will show
up as architecture.

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
trap `build.sh` produces.

`tools/jockc.sh run` is the cheap door and was badly
under-used here: it compiles and evaluates a small program in
seconds, with no kernel and no trap. Both corrections in this file
— items 4 and 5 — were settled by a ten-line program through
`jockc.sh run`. The expensive path is for artifacts, not for
questions.

## 9. No ambient context for a callee

Arvo `+spin`s a vane with `[duct eny dud]` so that the vane's own
arms stay narrow and the context is implicit. Jock has nothing
like it, so every vane arm carries the context explicitly:
`call(s, duct, task)`, `take(s, duct, wire, sign)`.

This is probably the *right* trade — the dependency is visible in
the signature, and Arvo's implicit spin is the kind of thing that
makes a vane hard to test in isolation.

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
- **Record update is a Nock edit, through nested paths.** See
  item 5: `t.v.d.blits = 7` edits at the axis and preserves
  siblings, which is the Hoon idiom's actual semantics and not an
  approximation of it.
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
