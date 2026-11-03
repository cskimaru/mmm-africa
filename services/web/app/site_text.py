"""Every piece of website text the officers can change, with its built-in default.

The officers' area builds its "Website text" form from this list, and the pages read the text through
`text(key)`. Officers' changes are stored by the directory service; an empty value goes back to the default.

Field kinds: "line" (one line), "text" (paragraphs: leave a blank line between them; [label](link) makes a link),
"choice" (one of `choices`).
"""

import re

from markupsafe import Markup, escape

PALETTE_CHOICES = [
    ("sunrise", "Savanna sunrise"),
    ("coast", "Coast"),
    ("highlands", "Highlands"),
    ("evening", "Evening"),
]


def f(key: str, label: str, default: str, kind: str = "line", **extra) -> dict:
    return {"key": key, "label": label, "default": default, "kind": kind, **extra}


GROUPS: list[dict] = [
    {
        "title": "Look and contact details",
        "fields": [
            f("site.palette", "Colour scheme", "sunrise", "choice", choices=PALETTE_CHOICES),
            f("contact.email", "Public email address", ""),
            f("contact.phone", "Public phone number", ""),
            f("contact.location", "Location shown in the footer", ""),
            f(
                "footer.about",
                "Footer description",
                "The African Chapter of the Medical Missionary Movement: national chapters across the continent, one "
                "family under MMM International.",
                "text",
            ),
        ],
    },
    {
        "title": "Home page: top",
        "fields": [
            f("home.kicker", "Small label above the headline", "Medical Missionary Movement · African Chapter"),
            f("home.hero_title", "Headline", "One continent. One calling. Healing in His name."),
            f(
                "home.hero_lead",
                "Introduction",
                "The MMM African Chapter brings together national chapters, health professionals, students and "
                "volunteers across Africa, one family under MMM International, carrying the healing ministry of Christ "
                "to every community on the continent.",
                "text",
            ),
            f("home.find_button", "First button", "Find a chapter"),
            f("home.start_button", "Second button", "Start a chapter"),
        ],
    },
    {
        "title": "Home page: the MMM family",
        "fields": [
            f("home.family_eyebrow", "Small label", "One movement, under one roof"),
            f("home.family_title", "Heading", "How the MMM family fits together"),
            f(
                "home.family_intro",
                "Introduction",
                "Every Medical Missionary Movement chapter belongs to one worldwide family. Here is where the African "
                "Chapter and its national chapters sit within it.",
                "text",
            ),
            f("home.tier_intl_label", "Worldwide level: label", "Worldwide"),
            f("home.tier_africa_label", "African level: label", "Across Africa"),
            f(
                "home.tier_africa_text",
                "African level: description",
                "Coordinates the national chapters across Africa, hosts the Annual Convention with a national chapter "
                "each year, and helps new chapters start.",
                "text",
            ),
            f("home.tier_national_label", "National level: label", "In each country"),
            f("home.tier_national_title", "National level: heading", "National chapters"),
            f(
                "home.tier_national_text",
                "National level: description",
                "Local leadership, outreach camps, student fellowships and church partnerships in each country.",
                "text",
            ),
        ],
    },
    {
        "title": "Home page: what we do",
        "fields": [
            f("home.pillars_eyebrow", "Small label", "What we do across Africa"),
            f("home.pillars_title", "Heading", "Four pillars of continental ministry"),
            f("home.pillar1_title", "Pillar 1: title", "Medical missions"),
            f(
                "home.pillar1_text",
                "Pillar 1: text",
                "Joint outreach camps and cross-border mission teams serving communities with little access to care.",
                "text",
            ),
            f("home.pillar2_title", "Pillar 2: title", "Training"),
            f(
                "home.pillar2_text",
                "Pillar 2: text",
                "Equipping health workers and students in whole-person care, health evangelism and servant leadership.",
                "text",
            ),
            f("home.pillar3_title", "Pillar 3: title", "Chapter growth"),
            f(
                "home.pillar3_text",
                "Pillar 3: text",
                "Helping believers start, organise and grow MMM chapters in their own countries.",
                "text",
            ),
            f("home.pillar4_title", "Pillar 4: title", "Fellowship"),
            f(
                "home.pillar4_text",
                "Pillar 4: text",
                "Bringing delegates together every year at the African Chapter Annual Convention.",
                "text",
            ),
        ],
    },
    {
        "title": "Home page: scripture and closing",
        "fields": [
            f(
                "home.verse_text",
                "Scripture",
                "And Jesus went about all the cities and villages, teaching in their synagogues, and preaching the "
                "gospel of the kingdom, and healing every sickness and every disease among the people.",
                "text",
            ),
            f("home.verse_ref", "Scripture reference", "Matthew 9:35"),
            f("home.chapters_eyebrow", "Chapters: small label", "National chapters"),
            f("home.chapters_title", "Chapters: heading", "Chapters of the African Chapter"),
            f("home.cta_title", "Closing banner: heading", "Serve with MMM Africa"),
            f(
                "home.cta_text",
                "Closing banner: text",
                "Volunteer, partner with a chapter, or help us start one in your country.",
            ),
            f("home.cta_button", "Closing banner: button", "Get in touch"),
        ],
    },
    {
        "title": "About page",
        "fields": [
            f("about.title", "Heading", "Medical Missionary Movement, African Chapter"),
            f(
                "about.intro",
                "Introduction",
                "The continental home of the Medical Missionary Movement in Africa, and part of MMM International.",
                "text",
            ),
            f("about.story_title", "Our story: heading", "A continental chapter of a global movement"),
            f(
                "about.story_body",
                "Our story",
                "The Medical Missionary Movement is built on the conviction that Christ's healing ministry is best "
                "expressed through practical medical service joined with the Gospel message. The African Chapter "
                "carries that mission across the continent.\n\n"
                "It links national chapters, such as the [MMM Kenya Chapter (MMMK)](/chapters/kenya), so they can "
                "share training, plan joint missions and meet each year at the African Chapter Annual Convention.",
                "text",
            ),
            f(
                "about.mission",
                "Our mission",
                "To unite and equip Christian health workers across Africa to combine medical service with Gospel "
                "ministry.",
                "text",
            ),
            f(
                "about.vision",
                "Our vision",
                "An MMM chapter in every African country, and compassionate, Christ-centred care within reach of every "
                "community.",
                "text",
            ),
            f("about.roles_title", "What we do: heading", "What the African Chapter does"),
            f("about.role1_title", "Role 1: title", "Coordinate"),
            f(
                "about.role1_text",
                "Role 1: text",
                "Bring national chapters together around shared plans and mission calendars.",
            ),
            f("about.role2_title", "Role 2: title", "Convene"),
            f(
                "about.role2_text",
                "Role 2: text",
                "Hold the Annual Convention, hosted by a different national chapter each year.",
            ),
            f("about.role3_title", "Role 3: title", "Plant"),
            f(
                "about.role3_text",
                "Role 3: text",
                "Support believers who want to start new MMM chapters in their own countries.",
            ),
            f("about.role4_title", "Role 4: title", "Train"),
            f("about.role4_text", "Role 4: text", "Share workshops and mentorship for health evangelism and missions."),
            f("about.role5_title", "Role 5: title", "Mobilise"),
            f("about.role5_text", "Role 5: text", "Assemble cross-border mission teams where the need is greatest."),
            f("about.role6_title", "Role 6: title", "Connect"),
            f(
                "about.role6_text",
                "Role 6: text",
                "Link African chapters with MMM International and the wider MMM family.",
            ),
        ],
    },
    {
        "title": "Chapters, leadership, events and contact pages",
        "fields": [
            f("chapters.title", "Chapters: heading", "Chapters across Africa"),
            f(
                "chapters.intro",
                "Chapters: introduction",
                "Each national chapter leads ministry in its own country as part of the African Chapter.",
                "text",
            ),
            f("chapters.start_title", "Start a chapter: heading", "Bring MMM to your country"),
            f(
                "chapters.start_intro",
                "Start a chapter: introduction",
                "New chapters usually grow from a small group of committed health workers and church members.",
                "text",
            ),
            f("chapters.step1_title", "Step 1: title", "Reach out"),
            f(
                "chapters.step1_text",
                "Step 1: text",
                "Tell us where you are and who is with you. We will connect you with the African Chapter leadership.",
            ),
            f("chapters.step2_title", "Step 2: title", "Gather a team"),
            f(
                "chapters.step2_text",
                "Step 2: text",
                "Form a core group, agree on leadership roles and begin meeting for prayer and planning.",
            ),
            f("chapters.step3_title", "Step 3: title", "Join the family"),
            f(
                "chapters.step3_text",
                "Step 3: text",
                "Be recognised as a national chapter, send delegates to the Annual Convention and begin outreach.",
            ),
            f("leadership.title", "Leadership: heading", "African Chapter leadership"),
            f(
                "leadership.intro",
                "Leadership: introduction",
                "The officers who coordinate the African Chapter.",
                "text",
            ),
            f(
                "leadership.empty",
                "Leadership: shown before leaders are added",
                "The African Chapter's leadership team will be listed here soon.",
            ),
            f("events.title", "Events: heading", "Shared activities"),
            f(
                "events.intro",
                "Events: introduction",
                "Gatherings the African Chapter holds with its national chapters, including the Annual Convention.",
                "text",
            ),
            f("contact.title", "Contact: heading", "Get in touch with the African Chapter"),
            f(
                "contact.intro",
                "Contact: introduction",
                "Questions about the African Chapter, starting a chapter, partnering or volunteering. For a national "
                "chapter's local programmes, contact that chapter directly.",
                "text",
            ),
        ],
    },
]

DEFAULTS: dict[str, str] = {fld["key"]: fld["default"] for g in GROUPS for fld in g["fields"]}


class SiteText:
    """Looks up text by key: the officers' version if they changed it, otherwise the default."""

    def __init__(self, saved: dict[str, str] | None) -> None:
        self.saved = {k: v for k, v in (saved or {}).items() if k in DEFAULTS and v.strip()}

    def __call__(self, key: str) -> str:
        return self.saved.get(key, DEFAULTS.get(key, ""))


# ---- Turning plain text into safe HTML ----

LINK = re.compile(r"\[([^\]\n]{1,200})\]\(((?:https?://|/|mailto:)[^)\s]{0,500})\)")


def inline(text: str) -> Markup:
    """Escape text, then turn [label](link) into links. Only web, site-relative and email links are allowed."""
    out, pos = [], 0
    for m in LINK.finditer(text):
        out.append(escape(text[pos : m.start()]))
        href = m.group(2)
        if href.startswith("http"):
            out.append(Markup('<a href="{}" rel="noopener" target="_blank">{}</a>').format(href, m.group(1)))
        else:
            out.append(Markup('<a href="{}">{}</a>').format(href, m.group(1)))
        pos = m.end()
    out.append(escape(text[pos:]))
    return Markup("").join(out)


def paragraphs(text: str) -> Markup:
    """Blank lines separate paragraphs; single line breaks are kept."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    return Markup("").join(
        Markup("<p>{}</p>").format(Markup("<br>").join(inline(ln) for ln in b.splitlines())) for b in blocks
    )


def rich(text: str) -> Markup:
    """Officer-written page bodies: paragraphs, "## Heading" lines and "- item" lists."""
    html: list[Markup] = []
    para: list[str] = []
    items: list[str] = []

    def flush_para() -> None:
        if para:
            html.append(Markup("<p>{}</p>").format(Markup("<br>").join(inline(x) for x in para)))
            para.clear()

    def flush_list() -> None:
        if items:
            html.append(
                Markup("<ul>{}</ul>").format(Markup("").join(Markup("<li>{}</li>").format(inline(x)) for x in items))
            )
            items.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_para()
            flush_list()
        elif line.startswith("## "):
            flush_para()
            flush_list()
            html.append(Markup("<h2>{}</h2>").format(inline(line[3:].strip())))
        elif line.lstrip().startswith(("- ", "* ")):
            flush_para()
            items.append(line.lstrip()[2:].strip())
        else:
            flush_list()
            para.append(line)
    flush_para()
    flush_list()
    return Markup("").join(html)
