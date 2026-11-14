"""
One mailbox, one account (FR-001): the canonical form of an email address.

Many mail services deliver several spellings of an address to the same mailbox:
`name+anything@...` (plus addressing) and, for Gmail, `n.a.m.e@gmail.com` or `@googlemail.com`.
Registration compares canonical forms, so one mailbox cannot be used for several accounts.
The address the user typed is still the one stored and used for login and emails.
Addresses of throwaway mailbox services (DISPOSABLE_DOMAINS) cannot register at all.
"""

GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}


def canonical_email(email: str) -> str:
    """`Na.Me+promo@GoogleMail.com` -> `name@gmail.com`; other domains only lose the `+tag`."""
    address = (email or "").strip().lower()
    local, separator, domain = address.rpartition("@")
    if not separator or not local:
        return address
    local = local.split("+", 1)[0] or local
    if domain in GMAIL_DOMAINS:
        local = local.replace(".", "") or local
        domain = "gmail.com"
    return f"{local}@{domain}"


# Well-known throwaway mailbox services: an account on them is not tied to a real person.
# Not a complete list; it stops the easiest way to create many accounts.
DISPOSABLE_DOMAINS = frozenset(
    {
        "10minutemail.com",
        "20minutemail.com",
        "dispostable.com",
        "dropmail.me",
        "emailondeck.com",
        "fakeinbox.com",
        "getairmail.com",
        "getnada.com",
        "guerrillamail.biz",
        "guerrillamail.com",
        "guerrillamail.de",
        "guerrillamail.info",
        "guerrillamail.net",
        "guerrillamail.org",
        "guerrillamailblock.com",
        "grr.la",
        "maildrop.cc",
        "mailinator.com",
        "mailinator.net",
        "mailnesia.com",
        "mintemail.com",
        "mohmal.com",
        "mytemp.email",
        "sharklasers.com",
        "spam4.me",
        "temp-mail.io",
        "temp-mail.org",
        "tempail.com",
        "tempmail.com",
        "tempmail.dev",
        "tempmail.plus",
        "tempmailo.com",
        "tempr.email",
        "throwawaymail.com",
        "trashmail.com",
        "trashmail.de",
        "yopmail.com",
        "yopmail.fr",
        "yopmail.net",
    }
)


def is_disposable_email(email: str) -> bool:
    """True for addresses on DISPOSABLE_DOMAINS or their subdomains (`x@abc.mailinator.com`)."""
    domain = (email or "").strip().lower().rpartition("@")[2]
    parts = domain.split(".")
    return any(".".join(parts[i:]) in DISPOSABLE_DOMAINS for i in range(len(parts) - 1))
