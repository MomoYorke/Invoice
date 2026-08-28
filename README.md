# Invoice

A local app to write invoices, keep them in a database, and produce both the
package your accountant needs and the figures you need. It runs on **Mac and
on Windows**, and everything stays on your own computer.

Your business name, address, UID, IBAN and logo go in **Settings**: there is
nothing personal inside the program itself, and what you type there is what
ends up on the invoices — in PDF and in Word — and at the top of the app.

The app speaks **Italian, English and German**; you switch with the small
control at the top right. Your clients' documents and emails follow a language
of their own, set on each client, because they are the ones reading them.

## The first time

The app opens on **First steps**: eight things, in order, each saying what it
is for, with a button that takes you where it is done.

Two of them are essential — who issues the invoice, and the IBAN — and until
they are filled in the app keeps opening there, because without them the
invoices come out incomplete. The other five are conveniences: the logo, the
clients, the first invoice, the mail, the session packs. Once the essentials
are in, the app opens on the Dashboard and what is left becomes a discreet
reminder at the top, which disappears by itself when you are done.

You can go back whenever you like, from that reminder.

## How to start it

On a **Mac**, double-click **`Invoice`** — the app with the icon. No black
window: it behaves like any other program on your Mac.
On **Windows**, double-click **`Start Invoice.bat`**. A black window appears
while it gets ready — a minute or two the first time, a few seconds after that
— and then **closes by itself**. The app stays open without it.

Either way the browser opens at `http://127.0.0.1:8471`.

**To close the app**, use the power button at the foot of the menu, inside the
app itself. It stops the program properly and tells you the tab can be closed.
Nothing is ever lost by closing it: everything you do is written down the
moment you do it.

> On a Mac there is also **`Start Invoice.command`**, which does exactly the
> same thing but in a Terminal window, showing what it is doing while it does
> it. Useful when something is not working; the black window has to stay open
> for as long as you use the app, because that window *is* the app.

> **Where you put the folder matters on a Mac.** macOS protects Desktop,
> Documents and Downloads: a program may only work in there with permission,
> and an app that has not been signed by a registered developer is never even
> asked - it is refused, silently. `Invoice` cannot start from those three
> folders (it will say so and stop, without touching anything). Put the app
> folder in your home folder, or anywhere else, and it runs. The Terminal
> version is unaffected, because the Terminal was granted that permission
> long ago.

> The first time on a Mac, macOS will refuse to open it: *"Apple could not
> verify it is free of malware"*. That is Gatekeeper, and it says nothing about
> the file — it blocks every unsigned script that arrived from the internet.
> Let it fail once, then go to **System Settings → Privacy & Security**, scroll
> down to **Security**, and click **Open Anyway** next to the line naming the
> launcher. Double-click it again and choose **Open**. Once, and never again.
>
> (Older guides say to right-click → "Open". That worked up to macOS Sonoma;
> from Sequoia on, Apple removed that shortcut for unsigned scripts.)
>
> If the button is not there, Terminal does the same thing — type
> `xattr -dr com.apple.quarantine ` and then drag the app folder onto the
> Terminal window to fill in the path.
>
> On a Mac that has never been used for development, the launcher may also
> trigger a macOS box asking to install the **command line developer tools**:
> that is where `python3` lives. Accept it, wait for it to finish, and start
> the app again.

> On Windows, install **Python** first: it is the one thing Windows does not
> bring by itself. Take it from
> [python.org](https://www.python.org/downloads/) and tick **"Add python.exe
> to PATH"** while installing. The launcher looks for it and says so plainly
> if it is missing, instead of failing later with something unreadable.
> Everything else — the libraries the app needs — it installs by itself the
> first time, which takes a minute or two.

> Also on Windows: **extract the zip before running anything**. Double-clicking
> the launcher from inside the zip window pulls out that one file on its own,
> without the program it is supposed to start, and it fails. Windows warns you
> about this, and it is right.
>
> Before extracting, right-click the zip → **Properties** → tick **Unblock** →
> OK. Do it on the zip, not afterwards on the files: the "came from the
> internet" mark is copied to every file as it comes out. Without it Windows
> greets the launcher with *"Windows protected your PC"* — click **More info**
> → **Run anyway** if it happens.
>
> Extract it somewhere OneDrive does not sync — `C:\Users\<you>\Invoice` is a
> good spot. Inside a synced Desktop or Documents, OneDrive tries to upload the
> 1'800 files of the Python environment while they are still being written.

> Coming from an older version, the data folders were named in Italian
> (`Fatture`, `Esporti`, `Cestino`, `Estratti conto`). The app renames them to
> `Invoices`, `Exports`, `Trash` and `Bank statements` the first time it
> starts, and repairs the paths it had recorded, so nothing goes missing.

If the app is already running, double-clicking only opens the browser without
restarting anything — **except when the program has been updated**: in that
case it restarts by itself, because the pages stay in memory from when it
started and you would otherwise keep seeing the old version.

## When a new version comes out

If you got the app from a repository, the launcher checks by itself whether a
newer version exists — not more than once every six hours, and without holding
up the start if there is no network. When it finds one it **shows what changed
and asks permission**: it never updates behind your back.

If you say yes, it first makes a backup of your data, then replaces the program
files, and installs any new libraries needed. **Your data is not touched**:
database, invoices, bank statements, backups and logo all live outside the
repository, so the update does not even see them.

To go back to the previous version, the number is in `data/.previous-version`:

    git reset --hard $(cat data/.previous-version)

That window stays almost empty: two lines at startup and that is it.
Nothing scrolls while you use the app, and there is no red warning to
interpret. If something goes wrong the page says so, and the full trace ends up
in `data/error.log`.

## The menu

The entries are grouped in the order things actually happen:

| Group | Entries | When you open it |
|---|---|---|
| — | Dashboard · Performance | every time |
| **Invoicing** | New invoice · Invoices · Sent emails | every week |
| **Your clients** | Clients · Credits · Sessions | every week |
| **Payments and tax** | Bank · Accountant | now and then |
| **The app** | Checks · Calculation check · Trash · Settings | when needed |

**Dashboard and Performance answer two different questions**, which is why they
are two pages. The *Dashboard* says **what you have to do now**: it greets you
by name, shows the revenue for the year so far and this month against last
month, then the list of what is outstanding — to collect, to send, packs run
out, bank statement to update — and finally recent activity. Every entry leads
exactly to the rows it counted. When there is nothing outstanding it says so,
and that is fine. *Performance* says **how you are doing**: monthly trend,
revenue by year, top clients, breakdown by service.

The safety nets — copies, calendar, calculation check, mail — live in
**Checks**: they are not things to look at every morning, they are things to
check when you check.

As long as anything is left from the **first steps**, a *First steps* entry
appears at the top of the menu with how many things are missing; when none are
left it disappears by itself.

When you open a detail, the entry of its list stays lit: an invoice's page
keeps *Invoices* lit, a pack keeps *Credits* lit.

**If you narrow the window** — to keep the app on half the screen next to
something else — below 1040px the menu shrinks to a strip of icons only (hover
to read the name). Up to 900px every page still fits whole; narrower than that
it is the individual tables that scroll inside their own box, and the page
never shifts sideways.

## What it does

- **Dashboard** — a greeting with today's date, revenue for the year to date
  compared with the same period last year, and this month against the month
  before (in January it looks back at December of the previous year; if the
  previous month was zero it does not invent a percentage). Then **To do** —
  invoices to collect, invoices not yet sent, packs run out, bank statement
  getting old, each one clickable — and **Recent activity**: invoices created
  and sent, sessions recorded, packs reaching zero, in a single list in time
  order. Where the time of day is not known, only the day is shown.
- **Performance** — revenue for the year, comparison with last year, projection
  to year end, collected vs outstanding, top clients, service types, charts.
- **New invoice** — pick client and service, the app assigns the sequential
  number, works out the totals (arithmetic in cents: no rounding errors) and
  produces **docx + PDF** in `Invoices/YEAR/`. For a monthly subscription it
  suggests by itself the month after the last invoice.
- **Invoices** — the full list (historical ones included), search, mark paid /
  to collect with one click. The *Sent* column shows the day and time the
  invoice left by email.
- **Clients** — the client register with total revenue for each.
- **Accountant** — one click and it prepares the package: Excel (register +
  monthly/quarterly summary + by client), a summary PDF and a copy of every
  invoice PDF of the year, already zipped. You will find it in `Exports/`.
  The package can have a language of its own, separate from the app's, because
  it is your bookkeeper who reads it.
- **Sessions** — the training sessions actually done, with day and time, most
  recent first.
- **Sent emails** — the diary of everything the app has sent, tests and failed
  attempts included.
- **Bank** — reads the bank statements and proposes which invoice was paid.
- **Credits** — tracking of session packs. Each client has a pack of credits
  (12 or 10 sessions); every session done consumes one. The page shows how many
  credits each person has left and flags with **"Credits used up"** whoever has
  finished a pack and needs invoicing again. The sessions come from your Google
  Calendar and are read automatically. When you issue the invoice for a pack,
  you link it from the same page: the sessions covered are marked with the
  invoice number and the pack closes. Next to the pack you see **which invoice
  covers it** and whether that invoice is *to collect* (amber) or *✓ collected*
  (green): the state updates by itself when you mark the invoice as paid.
- **Hide amounts** — the **eye** button at the top of the Dashboard (and the
  same eye at the bottom of the menu) blurs every amount: useful for
  screenshots or when you are in a public place. Open eye = amounts visible,
  crossed-out eye = amounts hidden. It stays on across every page until you
  turn it off.
- **Checks** — verifies numbering (duplicates, gaps) and amounts, and holds the
  safety-net panel.
- **Settings** — business details that end up on the invoice (IBAN, address…),
  the email templates, and the backup folder.

## The logo

You upload it in **Settings → Logo**. It applies everywhere: on the PDF
invoices, on the Word ones, and at the top left of the app. A PNG with a
transparent background is best; a JPG works too.

It does not need to be the right size. In the Word invoice the logo's space has
a fixed, fairly wide shape: if your logo is square it is not stretched, it is
simply given some air on either side.

Until you upload one, the app shows a grey placeholder — but **on the invoices
that space stays empty**, so a document never goes out with "upload it in
Settings" printed on it.

The file ends up in `data/logo.png`, together with your other data. If you pass
the app on to someone else, your logo does not follow it.

## Where the data comes from

On first start, if you point Settings at an **archive folder**, the app imports
what is in it: invoices in Word and PDF, a `clients.json`, the Excel summaries
of past years. That folder is **never modified**: the app only reads it. New
invoices are born in here, in `Invoices/YEAR/`.

For the years before the app, the official totals come from the Excel summaries
(more complete than the individual Word invoices of those years).

## Session credits — the rules

**Whoever works on credits is declared in the app**, under *Credits → Who works
on credits*. Each person needs four things:

| Field | What it is for |
|---|---|
| Name | how they appear in the app and in the register |
| Word in the calendar | the app counts as their session every event containing this word. Pick one that will not turn up by accident elsewhere |
| Sessions per pack | how many credits a pack gives |
| Price | when you issue an invoice for that amount, the app works out by itself that they bought a pack and gives the credits back |

Two fields are rarely used:

- **Make the invoice out to** — when the person training and the person paying
  are two different people.
- **Is the supplement of** — for someone who trains as a couple and pays a
  reduced pack in addition to the other person's. On days when the other one is
  absent, the session is a full one and comes off the other person's pack.

Someone who stops is **archived**, not deleted: their name stays recognisable
in the calendar titles (needed if a shared pack is still open) but no new packs
are opened for them. The app refuses to delete anyone who already has packs in
the register.

People who pay per single session, or by monthly invoice, do not belong here.

- **Invoices attach themselves.** When you issue a pack invoice, the app
  recognises whose it is from the amount and the addressee, and: opens the new
  pack if the old one has run out; or links it to the one in progress if that
  did not look paid yet; or holds it **pending** and uses it for the next pack.
  Invoices for a monthly subscription do not touch the credits.
- The amounts recognised are the ones written on each client's card.
- You can always link a past invoice **by hand** to any pack, from the button
  on the Credits page. Linking never closes a pack that still has credits.
- A **cancelled session still consumes the credit**.
- **Future appointments do not count**: only sessions up to today.
- The session history (up to 19.08.2026) is **frozen and validated** against
  the real invoices: syncing appends, it never rewrites the past.
- Every session carries its Google event ID: running the sync ten times does
  not create duplicates.
- The historical calendar, if you connect one, is never read by the credits.
- States: *In progress* · *Running low* (2 or fewer left) · **Credits used up**
  (pack finished: issue the next invoice).
- The register is `sessions.json` (backed up on every save in `data/backups/`).

## Which services the app recognises

Looking at the lines of an invoice, the app has to work out **which service you
sold**: the Dashboard needs it to group revenue, and the email needs it to name
the service and pick the right text.

You write the rules yourself, in **Settings → Services the app should
recognise**. One line per service:

```
Service name = word, word
```

The words are the ones that appear in the lines of your invoices. Without `=`,
the name doubles as the word. There are two lists, and the difference matters
because it decides which text goes in the email:

| List | What it is | In the email |
|---|---|---|
| **By subscription** | renews every month | "this month's invoice", and the month goes in the subject |
| **By pack** | bought once and used up | "your invoice", no month |

The **first line that matches** wins, and subscriptions are tried first: if a
word appears in both lists, put the more specific one on top.

A physiotherapist, for example:

```
By subscription:  Rehabilitation = rehabilitation
By pack:          Physiotherapy = session, sessions, physiotherapy
```

**If you leave the lists empty** the app does not try to guess: on the
Dashboard all revenue ends up under *Other*, and the email says "Please find
attached your invoice." without naming anything. That is deliberate: naming the
wrong service in an email that goes to a client is worse than not naming one.

## How to read "by service type"

The sum of the entries always matches the revenue for the year:

- **discounts** (a loyalty discount, say) do not get an entry of their own: they
  are **subtracted from the service on the same invoice**, even though on the
  document they appear as a positive amount (2'050 − 50 = 2'000);
- invoices **with no detail lines** (imported from a PDF) are traced back to
  their service when it can be deduced without ambiguity — same client, same
  exact amount, only one possible service — and otherwise end up under *Not
  itemised*, so they never disappear from the count.

## Sessions from the calendar

The app reads the session calendar by itself and deducts the credits. You
connect it once: Google Calendar → your calendar → calendar Settings →
*Secret address in iCal format*, and you paste that address into Settings. A
historical calendar, if you have one, must never be connected here.

The app does not ask you for the calendar's name: it lets the calendar itself
say it, and from then on calls it by name in its pages.

The reading happens when you open the Credits page, not more than once every 15
minutes; the *Refresh now* button forces it. If the calendar does not answer
you see the credits from the last successful reading, with a notice — never an
error page in place of your data.

**Why iCal and not the Google API.** No Google Cloud project, no authorisation
to renew, no password: one address to paste. In exchange, iCal describes a
recurring series as a single entry plus its exceptions, whereas the API handed
you a ready-made event for each repetition. The repetitions are therefore
expanded in `core/calendar_feed.py`, and the identifier that stops the same
session being counted twice is **UID + date**.

All the earlier rules still hold: window from 20.08.2026, future sessions do
not consume credits, ones cancelled on Google do not count, the couple rule
applies. Two sessions for the same client on the same day are legitimate (it
happens with shared packs) and both are counted.

## Sessions (the list)

The **Sessions** entry in the menu lists the training sessions **actually
done**, one per credit consumed, most recent first. Appointments still to come
do not appear; cancelled ones do, marked, because they consumed the credit.

The two sources are deliberately kept apart:

- **which** sessions: the credit register (`sessions.json`), the only list that
  is complete and already checked against the invoices. The Google calendar is
  not: when a repeating series ends, its past disappears with it.
- **at what time**: the calendar, kept in a separate index
  (`data/orari.json`). It can be deleted and rebuilt whenever you like without
  touching the credits.

The *Refresh the times from the calendar* button fills in the missing times.
For the oldest sessions the time is unknown, because the session calendar no
longer holds them: they fill in by themselves if you also paste into Settings
the iCal address of a **historical calendar**. That second address serves the
Sessions list only — the credits never go near it, so there is no way a session
gets counted twice.

## Sending the invoice by email

From an invoice's page, **✉️ Send by email**.

The mail leaves from your own server (port 587), not from Gmail: if your domain
only authorises its own server to send in its name (SPF `-all`), anything sent
from Gmail lands in spam. Watch the host name: the certificate often covers
`yourdomain.ch` but **not** `mail.yourdomain.ch`, in which case you write the
first — the app tells you if you get it wrong. The mailbox password goes into
Settings once.

**How the sending page works**

1. The text arrives already written, modelled on the emails you really send,
   and you can rewrite it entirely before sending.
2. *Test to yourself* sends the identical mail to your own address: you see it
   arrive exactly as the client will.
3. *Send* sends it to the client and records the date. If you try again, the
   page warns you that it is already marked as sent.

**The two text templates.** The middle sentence — the one that changes from
mail to mail — has two versions saved in Settings: one for *Subscription*, one
for *Session pack*. The app picks which to use by looking at the invoice lines,
and on the sending page two buttons let you switch with *Rewrite with this
template*. Rewriting rebuilds the text from scratch, so do it before you touch
it by hand. The rest of the mail (the opening, the standing-order sentence, the
sign-off) stays automatic.

**One template per language.** You write the email text, so the app cannot
translate it — those are your words. It can however keep one version per
language and use the one matching the **client's** language. In Settings, four
tabs — *For everyone*, Italiano, English, Deutsch — swap the fields without
reloading; they are all in the same form, so Save saves them together. Where
you write nothing, the "for everyone" version is used, so leaving all of it
alone changes nothing.

**Your sign-off** is a field of its own, outside the templates, and is never
translated. If it lived inside them, every translated version would keep a copy
of it, and changing your phone number would update only one.

**When the invoice goes to someone else.** The person training and the person
receiving the invoice are not always the same: a parent, a spouse, a company.
The client's card has a **Make the invoice out to** field: when filled in, the
document and the register carry that name, while the **file name stays the
client's** (`Anna #88.pdf`), so new documents stay in line with the old ones.
On the *New invoice* page, once you have picked the client, the app reminds you
before you produce the document. The address stays the one on the card.

**What changes from client to client** (set on the Clients page)

- *Email*: without an address, the Send button stays off.
- *Language*: which language their documents and emails come out in.
- *Your sign-off*: the two sign-offs are written in Settings, here you pick
  which one to use with this person.
- *Monthly subscription*: adds the standing-order sentence and makes it say
  "this month's invoice" instead of "your invoice" — because a ten-session pack
  is not monthly.

**The register.** The **Sent emails** entry in the menu lists everything that
left the app: day and time, recipient, subject, attachments, and which folder
the copy ended up in. Clicking *read* reopens **the whole message**, with
sender, blind copy and the exact text the client read — one message weighs
about 250 bytes, so ten years of invoices fit in a little over a hundred
kilobytes. Tests to yourself and failed attempts go in too, with the reason: a
list that shows only the successes is useless precisely when you need it. Rows
for invoices sent before the register existed were reconstructed from the date
written on the invoice, and say so. This list is the app's diary: the real
emails stay where they have always been.

**The copy to yourself.** Every invoice sent also arrives in your own inbox, as
a **blind copy**: the client does not see it (it is Bcc, not Cc — and the
header does not even travel in the message they receive). It exists because a
POP account in Mail does not show the server's Sent folder: this way you can
still find the invoice you sent in Mail, by searching. You turn it off in
Settings with a checkbox.

**The copy in "Sent".** SMTP only delivers mail: the copy in the Sent folder is
written by whoever sends, which is why mails sent from an iPhone also show up
on the Mac. The app does the same, depositing the message over IMAP right after
sending. So you find sent invoices in Sent like every other mail, from Mail,
from the phone, from webmail. It finds the folder by itself (the server marks
`INBOX.Sent` as Sent). If the copy fails the mail has still gone out, and the
app tells you instead of pretending otherwise. *Test to yourself* deposits its
copy too: a test that skips the deposit would not test the thing that matters.

**Two invoices in one mail.** On the sending page you can attach another recent
invoice as well, even one belonging to a different client: the typical case is
someone who gets their own plus their spouse's. The opening becomes "Attached
are two invoices". Only invoices made with the app in the last 90 days and not
yet sent are offered: the old ones from the archive exist only in Word and
cannot be attached as PDFs.

## Knowing when you have been paid

Download the transactions from your e-banking and drop the files into
**`Bank statements/`**. The app reads three formats:
**camt.053 / camt.054** (XML), **CSV**, and **PDF statements**. In a CSV it
recognises the columns by their header names, because every bank writes them
differently. Then you open the **Bank** page.

The PDF deserves an explanation. When the text is extracted, the *Debit* and
*Credit* columns collapse into one and you could no longer tell whether an
amount went in or out. The sign is recovered from the **balance**, which cannot
lie: transactions are listed most recent first, and the balance of the row
below, plus or minus the amount, must give back the balance of the row above.
If it works out with a plus it is a credit, with a minus a debit, and if it
works out with neither the row is discarded rather than guessed at. If the
figures fail on more than one row in ten, the app rejects the whole file and
tells you to download the CSV: nothing is better than an invented list.

**Automatic matching.** When the app starts, and every time you open the Bank
page, the payments where there is nothing to decide are matched by themselves:
exact amount, **one single** strong candidate, and the client's name (or the
invoice date) in the reference text. Everything else is still asked of you.
Tested against 18 months of real statements before it was switched on: **30
automatic matches, 30 correct, none wrong**, and the 19 doubtful cases stayed
doubtful. Every row decided by the app stays marked "by the app" and is undone
with one click. It is switched off in Settings.

Rules that do not change:

- **The app never marks anything by itself.** It proposes and waits for
  confirmation. A wrong match made silently is worse than no match: it would
  have you believe you had been paid when you had not.
- It reads **incoming payments only**. What you spend, it does not look at.
- Files are neither moved nor modified, and the same month downloaded twice
  does not produce duplicates (every payment has its own fingerprint).
- *Undo* puts the invoice back exactly as it was, state included.

How they are matched: exact amount, a window of **60 days** before the payment
(5 after, for those who pay in advance) and the client's name looked for in the
reference — including written without umlauts, as banks do ("Mueller" or
"Muller" for Müller). The window is deliberately narrow: monthly subscriptions
are all for the same amount, and with six months of leeway every payment would
find six identical invoices.

Three more cases that really happen, and that the app handles:

- **The date in the reference.** Some clients write not the invoice number but
  its date ("INVOICE 21-04-26"). It is the most precise clue there is without a
  QR-bill, and it tells apart two identical monthly invoices from the same
  client.
- **The payer is not the addressee.** The name arriving in the account is the
  husband's, the wife's, a company's. The payer's name goes on the client's
  card, field *On the bank statement pays as* (several names separated by
  semicolons).
- **One transfer, two invoices.** Two invoices for the same household paid with
  a single transfer. If no single invoice makes that amount, the app looks for
  combinations of two or three invoices **from the same client** that make it
  exactly. Same client only: without that constraint it would find sums that
  add up by coincidence.

Invoices already ticked *paid* by hand stay proposable: confirming them does
not change the state, it adds the real payment date, and the row says so. It
pays to work from the top down (the list is already in time order): every
confirmation removes that invoice from the candidates for the following ones,
and ambiguities between identical monthly invoices resolve themselves.

- 🔵 amount and name match → a *Confirm* button
- ⚪️ only the amount matches → the app shows the candidates and lets you choose
- 🟢 the payment reference matches → this will appear with QR-bills, and from
  there the match will no longer be a hypothesis

The reference is **not** deduced from the invoice number: another creditor's
reference can end with the same digits, and the app would say "certain" about
the wrong invoice. Only a reference the app itself printed counts.

When you confirm, the invoice takes the real payment date (`paid_at`) as well
as the state *paid*: a tick put there by hand and the day the money arrived
stay two different pieces of information.

**Who has not paid yet.** On the Dashboard the app separates two things that
look alike and are not: invoices **genuinely outstanding** — issued long enough
ago that the payment should already have shown up in the statement you have —
and those **too recent to tell**, whose payment will land in a statement you
have not downloaded yet. The boundary is 45 days before the last transaction
read. Without this distinction the list of late payments would be full of false
alarms and you would stop looking at it.

The *safety nets* panel in Checks shows how far the statements reach and turns
amber after 40 days: that is the reminder to download a new one.

## Backups

Two nets, not one.

**Inside the app** (`data/backups/`): a copy of the database alone, at every
start and before every operation that could destroy data. It is there to take
you back half an hour, not to survive a broken disk — it sits on the same disk.

**Off the computer**, in a folder that syncs itself somewhere else: iCloud
Drive on a Mac, OneDrive on Windows, and *Documents* when neither is there. The
folder is called *Invoice - Backup*; installations that started out in Italian
keep the name they already had, *Fatture App - Backup*, because what is written
in Settings always wins over the default. Two archives go in it.

- `fatture-app-YYYYMMDD-hhmmss.zip` — database, session register and the PDFs
  in the `Invoices/` folder. Created at startup (once a day) and **after every
  new invoice**. About 140 KB. The last 30 copies are kept, plus the first of
  each month, which is never deleted.
- `storico-YYYYMMDD-hhmmss.zip` — the documents in the archive folder, where
  the invoices older than the app live. A few MB, so it is remade **only when
  that folder really changes**: the app compares its fingerprint and if it is
  identical it rewrites nothing. Three are kept. The folder is only read, never
  modified.

As soon as it is written, every archive is reopened: the database inside must
pass `PRAGMA integrity_check` and hold the same number of invoices as the
original. If it does not pass, the archive is thrown away and the error appears
in Settings. A backup that does not reopen is not a backup.

In Settings you find the date of the last copy, the last ten, a *Make a copy
now* button, and the destination folder, which you can change.

## Practical notes

- Prices: write them the way you are used to (`110.-`, `1'800.00`,
  `150,00 CHF`).
- The invoice number is automatic (highest existing + 1); the app refuses
  duplicates and never overwrites existing files.
- Deleted invoices end up in `Trash/` inside this folder.
- Backup: just copy this folder (the database is `data/fatture.db`).

## Trying the app without touching real data

These environment variables divert the app onto a copy. They are for anyone
putting their hands in the code: you get to run real tests, with real data,
without risking your own.

| Variable | Diverts |
|---|---|
| `INVOICE_DB` | the database |
| `INVOICE_DIR` | the folder where documents end up |
| `INVOICE_SESSIONS` | the session register |
| `INVOICE_STATEMENTS` | the bank statements |
| `INVOICE_TIMES` | the session times |
| `INVOICE_LOGO` | the logo |
| `INVOICE_BACKUP` | the backups |
| `INVOICE_PORT` | the port (8471 by default) |

They used to be called `FATTURE_*`, and those names still work: a test script
that uses them does not break on an update.

One more diverts nothing: `INVOICE_OPEN_BROWSER=1` tells the app to open the
browser itself, the moment it has taken the port. The Windows launcher uses it,
because that is the only place that knows for sure the app is up; the Mac one
waits and opens the browser on its own, the way it always has.

`INVOICE_BACKUP` also takes precedence over the saved setting: a test app
almost always starts from a copy of the real database, and without this it
would drop its copies in among the good ones — where, with the rotation of the
last 30, they would end up pushing the real ones out.
