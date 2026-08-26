Drop in here the bank statements you download from your e-banking.

Formats the app reads:
  - camt.053 / camt.054  (XML)  <- the best one: it is the Swiss standard, the
                                   same at every bank, and it carries the name
                                   of whoever paid and the payment reference
  - PDF                          <- works: the app works out money in and money
                                   out from the balance column, and if the
                                   figures do not add up it rejects the file
                                   instead of guessing
  - CSV / TSV                    <- works, but every bank writes it its own way

What the app does with these files:
  - it READS them, nothing else. It does not move them, change them or delete
    them.
  - it looks at INCOMING payments only. What you spend, it does not even open.
  - it proposes the match with your invoices, and waits for you to confirm.

You can download the same period several times over: payments already seen are
not counted twice.

Then open the "Bank" page in the app's menu.
