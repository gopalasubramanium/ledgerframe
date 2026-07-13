# GitHub Issues disclaimer — PROPOSED (release-readiness Gate B10 / RD-7)

**Status: PROPOSED. 🛑 Owner ratifies the copy before it goes live.**

RD-7 keeps Issues **enabled**, with a visible disclaimer defining support boundaries and response
expectations. Two drafts below: the **pinned issue / README banner** (the long form) and the
**issue-template header** (the short form a person actually reads at 2am while opening an issue).

The tone is deliberate. Silence, or a boilerplate "we value your feedback", is what turns a
single-maintainer project's issue tracker into a graveyard of resentment. **Saying plainly what will and
will not happen is kinder than implying a service that does not exist.**

---

## A. Long form — pinned issue: *"Read this before opening an issue"*

> ### Support boundaries — please read
>
> LedgerFrame is a **single-maintainer, single-user, local-first** project. Issues are **open** because
> they are useful, not because there is a support desk behind them.
>
> **What you can expect**
>
> - Issues are read. Not necessarily quickly.
> - **There is no SLA and no guaranteed response time.** Some issues will be answered in a day, some in
>   a month, and some will sit. That is not rudeness — it is one person.
> - Bugs with a **clear reproduction** are the most likely to be fixed, by a wide margin.
> - **Not every issue will be actioned, and some will be closed without being fixed.** That will be said
>   directly rather than left to rot with silence.
>
> **What issues are good for**
>
> - 🐛 **Bugs** — especially anything where the app showed a **wrong number**, or a number where it
>   should have honestly shown nothing. That is the product's central promise; a violation of it is the
>   most serious kind of bug this project has.
> - 📖 **Documentation that is wrong or misleading** — including install steps that do not work on your
>   machine. If the README told you something untrue, that is a defect, and we want it.
> - 💡 **Feature requests** — welcome, with the honest caveat that the roadmap is long and the
>   maintainer is one person. See `ROADMAP.md`; several things you may be about to ask for are already
>   on it, and marked as not built.
>
> **What issues are NOT for**
>
> - 🔒 **Security vulnerabilities.** Do not post these publicly. See [`SECURITY.md`](SECURITY.md) — mail
>   **security@ledgerframe.org**.
> - 💰 **Financial or investment advice.** LedgerFrame **reports; it does not advise**, and neither does
>   its issue tracker.
> - 🏢 **Commercial support requests.** There is no support contract to buy.
>
> **Before you open one**
>
> - Run `./scripts/doctor.sh` and paste the output — it answers a surprising number of install issues.
> - Say what you actually ran, what you expected, and what happened.
> - Include your OS, architecture, and how you installed. *(If your platform is not in the README's
>   **Tested on** table, say so — that is useful information, not a disqualification.)*

---

## B. Short form — issue-template header

> **Before you post:**
> **Security bug? Do not open an issue — email security@ledgerframe.org** ([`SECURITY.md`](SECURITY.md)).
>
> This is a single-maintainer project. Issues are read, but **there is no SLA and no guaranteed response
> time**. Bugs with a clear reproduction get fixed first. Not every issue will be actioned — and if it
> won't be, you will be told, rather than left waiting.
>
> Wrong-number bugs are the highest priority this project has: if LedgerFrame showed you a figure that
> was **incorrect**, or showed a figure where it should honestly have shown **nothing**, say so first.

---

## Notes for the owner

- **The wrong-number emphasis is deliberate.** It routes the reports that matter most to this product
  straight to the top, and it tells users, in the place they are most likely to read it, what the
  project actually cares about.
- **Both drafts link to `SECURITY.md`, which does not exist yet** — it is blocked behind **B7** (mailbox
  verification). **These links are dead until B8 ships.** Do not publish either draft before then, or
  the disclaimer sends people holding a vulnerability to a 404.

**🛑 STOP — owner ratifies.**
