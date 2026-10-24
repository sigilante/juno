#!/usr/bin/env python3
#  tools/test.py:  drive the juno kernel through Arvo's own outer
#  interface and check what comes back.
#
#  This runs the kernel the way a runtime does: it reads the arms
#  off their Arvo axes (+4 load, +10 wish, +22 peek, +23 poke) and
#  fires +23 with Arvo's sample, [now ovo].  Nothing here knows
#  anything about Jock.
#
#  Usage:  test.py out/juno-core.jam
#
#  The argument is the EVALUATED core, not the trap build.sh
#  emits: kicking the trap means running the Jock compiler, and
#  under a pure-python Nock that does not finish.  Let honk-kick
#  evaluate the trap in rust and pass its product here.
import sys

sys.path.insert(0, __import__("os").environ.get(
    "JOCK", __import__("os").path.expanduser("~/Code/jock")) + "/tools")
import vexrun  # noqa: E402

SLAM = (9, (2, (10, ((6, (0, 3)), (0, 2)))))


def cord(s):
    """a jock/hoon term or string: bytes, least-significant first"""
    return int.from_bytes(s.encode(), "little")


def path(*terms):
    """a wire: a null-terminated list of terms, outermost first"""
    out = 0
    for t in reversed(terms):
        out = (cord(t), out)
    return out


def lst(n):
    out = []
    while isinstance(n, tuple):
        out.append(n[0])
        n = n[1]
    return out


def unco(n):
    """render a noun, turning plausible terms back into text"""
    if isinstance(n, tuple):
        return "[%s %s]" % (unco(n[0]), unco(n[1]))
    if 0x20 <= (n & 0xFF) <= 0x7E and n > 0xFF:
        try:
            b = n.to_bytes((n.bit_length() + 7) // 8, "little")
            if all(0x20 <= c <= 0x7E for c in b):
                return "%" + b.decode()
        except Exception:
            pass
    return str(n)


def arm(core, ax):
    return vexrun.nock(core, (9, (ax, (0, 1))))


def fire(core, ax, sample):
    return vexrun.nock((arm(core, ax), sample), SLAM)


def main(argv):
    #  vexrun's nock is recursive and so is everything the prelude's
    #  list helpers do, so the default python limit is reached long
    #  before the kernel does anything interesting.
    sys.setrecursionlimit(200_000)
    core = vexrun.cue(open(argv[0], "rb").read())
    vexrun.STEP_BUDGET = 500_000_000
    fails = []

    def ck(name, got, want):
        ok = got == want
        print("  %-28s %s" % (name, "ok" if ok else
                              "FAIL got %r want %r" % (got, want)))
        if not ok:
            fails.append(name)

    print("ABI: arms on Arvo's axes")
    for ax, nm in ((4, "load +4"), (22, "peek +22"), (23, "poke +23")):
        ck("%s is an arm" % nm, isinstance(vexrun.slot(core, ax), tuple),
           True)
    #  +10 is +wish's slot and this kernel impls the three-arm trait,
    #  so the adapter puts a CRASH FORMULA there.  It must be a
    #  formula -- the bare atom that used to sit here was not one, so
    #  the runtime met a malformed arm rather than a refusal -- and it
    #  must bail when fired.  Both halves are the contract.
    ck("wish +10 is a formula", isinstance(vexrun.slot(core, 10), tuple),
       True)
    try:
        vexrun.nock(core, (9, (10, (0, 1))))
        ck("wish +10 refuses when fired", "did not crash", "a crash")
    except vexrun.Crash:
        ck("wish +10 refuses when fired", True, True)

    #  SHORT PATH: an event routed straight to %d.  The ovum's wire
    #  head names the vane (+gest), so /d reaches dill with wire ~.
    #  dill gives %blit on the duct the loop built, whose one frame
    #  is [%$ ~] -- so the pop lands on the runtime and the gift
    #  leaves as an ovum.  pass -> call -> give -> outside.
    print("\nshort path: /d %text -> dill gives %blit to the runtime")
    vexrun.STEPS = 0
    fx, k1 = fire(core, 23, (1, (path("d"), (cord("text"), cord("hi")))))
    print("    fx =", unco(fx), " (%s steps)" % f"{vexrun.STEPS:,}")
    ck("one ovum out", len(lst(fx)), 1)
    ovum = lst(fx)[0]
    ck("ovum wire is ~", ovum[0], 0)
    ck("ovum mark is %blit", ovum[1][0], cord("blit"))
    ck("ovum carries the payload", ovum[1][1], cord("hi"))
    ck("dill counted one blit", fire(k1, 22, path("blits")), 1)
    #  dill stamps mien.now into its own state, so a non-zero
    #  .last is the only outside evidence that the context was
    #  really handed down rather than built and dropped.
    ck("the Mien's clock reached dill", fire(k1, 22, path("last")), 1)
    ck("echo untouched", fire(k1, 22, path("echoes")), 0)
    ck("now was taken from the event", fire(k1, 22, 0), 1)

    #  LONG PATH: an event routed to %e, which PASSES to %d.  The
    #  duct therefore grows to two frames, dill's give pops the
    #  inner one back into echo's +take, and echo's own give pops
    #  the outer one to the runtime.  This is the only path that
    #  exercises +take and a duct deeper than one.
    print("\nlong path: /e %echo -> echo passes %d, takes, gives %ack")
    vexrun.STEPS = 0
    fx2, k2 = fire(k1, 23, (2, (path("e"), (cord("echo"), cord("yo")))))
    print("    fx =", unco(fx2), " (%s steps)" % f"{vexrun.STEPS:,}")
    ck("one ovum out", len(lst(fx2)), 1)
    o2 = lst(fx2)[0]
    ck("ovum wire is ~", o2[0], 0)
    ck("ovum mark is %ack", o2[1][0], cord("ack"))
    ck("payload survived the round trip", o2[1][1], cord("yo"))
    ck("dill was called again", fire(k2, 22, path("blits")), 2)
    #  stronger than the short path: this dill call happened inside
    #  a NESTED pass, so .last == 2 proves the Mien vcall built mid
    #  loop carried THIS event's time and not the previous one's.
    ck("nested call saw the new event time", fire(k2, 22, path("last")), 2)
    ck("echo took one sign", fire(k2, 22, path("echoes")), 1)

    #  +load/+4: the migration arm.  Feeding it the state exported
    #  by the live kernel must give a kernel that answers the same.
    print("\nload +4: graft the running state into a fresh kernel")
    #  the kernel is [kbatt st pokeg peekg loadg], so the exported
    #  state sits at axis 6 -- the head of the payload.
    k3 = fire(core, 4, vexrun.slot(k2, 6))
    ck("loaded kernel answers blits", fire(k3, 22, path("blits")), 2)
    ck("loaded kernel answers echoes", fire(k3, 22, path("echoes")), 1)
    ck("loaded kernel answers dill's clock", fire(k3, 22, path("last")), 2)

    print("\n%s" % ("FAILED: " + ", ".join(fails) if fails else "all ok"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
