# "Tested on" — TEMPLATE (release-readiness Gate B6 / RD-4)

**Status: TEMPLATE. 🛑 The OWNER fills this in and signs it. Automation must not.**

> ⚠ **AUTOMATION HAS DELIBERATELY LEFT THIS EMPTY.** Not because it could not guess — it could have
> written "Debian 12, Ubuntu 24.04, Raspberry Pi OS, x86-64, arm64" in a second, and every row would
> have *looked* right. **Every one of them would have been a claim nobody had checked.**
>
> **A "tested on" row is a promise.** RD-4 asks for the **narrowest TRUE claim**, and a platform list
> the project cannot back is the same defect class as a fabricated figure: a number we never ran,
> presented as fact. This product's entire premise is that it does not do that.

---

## The rule for this table

**A row may be added ONLY when the owner has personally run the full suites clean on that exact
OS + architecture.** Not "it should work". Not "it's Debian-based, so…". **Run, clean, then written
down.**

"Clean" means, on that machine:

```bash
make test                          # backend suite — all green
( cd frontend && npm run check )   # lint · typecheck · tokens · unit · Playwright — exit 0
./scripts/install.sh --dry-run     # the installer plans without error
./scripts/doctor.sh                # no CRITICAL failures
```

**If a platform has not had that done to it, it does not go in the table.** Leaving it out costs a
user one question. Putting it in wrongly costs them a broken install and their trust.

---

## The table

| OS + version | Architecture | Python | Node | Suites clean (date) | Verified by |
|---|---|---|---|---|---|
| [OS AND VERSION] | [x86-64 / arm64 / …] | [3.x] | [20.19+ / 22.12+ / …] | [YYYY-MM-DD] | [OWNER] |
| | | | | | |
| | | | | | |

---

## The statement that goes in the README

Fill only from the table above — **nothing may appear here that is not a row up there.**

> **Tested on:** [list the rows, verbatim].
>
> Other platforms may work; **we have not tried them and make no claim.** If you run it somewhere else
> successfully, tell us and it will be added — after it has been verified, not because it was reported.

---

## What may NOT be claimed until CI exists

There is **no CI pipeline** in this repository (verified — release-readiness §1-2f / RD-4). Until there
is one:

- ❌ no "supported platforms" claim — *supported* implies someone is watching it stay working;
- ❌ no "continuously tested" / "CI-verified" badge or wording;
- ❌ no matrix of versions the project is not actually running.

✅ What may be claimed is exactly this: **"the suites ran clean on these machines, on these dates."**
That is a fact, and it stays true whether or not anyone is watching.

---

**🛑 STOP — owner fills the table and signs it. It ships empty rather than wrong.**
