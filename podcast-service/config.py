"""Show configuration for the daily podcast.

Everything worth changing lives here: the show name, the rotation lists and
the feeds. No keys, no logic.
"""

import os

SHOW_TITLE = os.getenv("SHOW_TITLE", "Brooksy on Code")
TARGET_WORDS = int(os.getenv("TARGET_WORDS", "1300"))

# Local time the full episode goes out, and the timezone it is judged in.
# Europe/London handles the BST and GMT switch on its own.
DELIVERY_HOUR = int(os.getenv("DELIVERY_HOUR", "7"))
TIMEZONE = os.getenv("PODCAST_TZ", "Europe/London")

# Episode counter, generated scripts and audio land here. Point it at a
# Railway volume if you want the numbering to survive a redeploy.
DATA_DIR = os.getenv("PODCAST_DATA_DIR", "/data/podcast")

FEEDS = [
    ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
]

# App of the day. One per episode, in order, wrapping round at the end.
APPS = [
    ("Obsidian", "Markdown notes stored as plain files on your own device, linked together."),
    ("Notion", "Docs, tables and light databases in one place. Good for a project brain."),
    ("Todoist", "Quick capture task list with natural language dates, syncs everywhere."),
    ("Google Keep", "Fastest way to get a thought out of your head on a phone."),
    ("Trello", "Cards on columns. The simplest way to see who is doing what."),
    ("Linear", "Issue tracking built for speed. Keyboard driven, no ceremony."),
    ("Fieldwire", "Site plans, tasks and snags on a phone, works with no signal."),
    ("Bluebeam Revu", "Mark up construction drawings properly instead of scribbling on PDFs."),
    ("Autodesk Construction Cloud", "Drawings, models and RFIs in one place for the whole team."),
    ("Procore", "Big-contractor project management: cost, programme, documents, the lot."),
    ("Dropbox", "Old but dependable file sync with proper version history."),
    ("1Password", "Passwords and secrets in one vault, shareable with family safely."),
    ("Bitwarden", "Free open-source password manager, self-hostable if you want."),
    ("Proton Mail", "Encrypted email that does not read your post to sell you things."),
    ("Signal", "Private messaging. Same idea as WhatsApp without the data harvesting."),
    ("Readwise Reader", "Read-it-later app that keeps every highlight you make."),
    ("Snipd", "Podcast player that clips and transcribes the bit you liked."),
    ("Otter.ai", "Records a meeting and hands you a searchable transcript."),
    ("Loom", "Record your screen and talk over it. Faster than writing an email."),
    ("Descript", "Edit audio by editing the transcript. Cut a word, cut the sound."),
    ("Canva", "Design without being a designer. Templates for anything client-facing."),
    ("Figma", "Where interfaces get drawn before anyone writes code."),
    ("Excalidraw", "Hand-drawn style diagrams. Perfect for explaining a system on a call."),
    ("Miro", "Infinite whiteboard for planning when a room full of people cannot meet."),
    ("Airtable", "A spreadsheet that behaves like a database. Good for small tools."),
    ("Zapier", "Joins apps together so a form filling in updates a sheet on its own."),
    ("Make", "Same job as Zapier with a visual canvas and cheaper heavy usage."),
    ("GitHub Mobile", "Review code and merge from the van. Notifications that matter."),
    ("Railway", "Deploys your code to a server without you learning server admin."),
    ("Supabase", "A hosted database with auth and storage bolted on. Postgres underneath."),
    ("Perplexity", "Search that answers with sources instead of ten blue links."),
    ("NotebookLM", "Feed it your documents, ask questions, get answers from those documents only."),
    ("Cursor", "A code editor with a model built in that can edit whole files."),
]

# Coding lesson rotation. Term plus the angle to take on it.
TERMS = [
    ("repo", "the single folder that holds a project and its whole history"),
    ("commit", "a saved checkpoint with a note explaining what changed"),
    ("branch", "a private copy of the work so you can try something safely"),
    ("merge", "folding a branch back into the main work"),
    ("pull request", "asking for your changes to be reviewed before they go in"),
    ("main branch", "the version everyone treats as the real one"),
    ("clone", "taking your own local copy of a repo"),
    ("fork", "your own copy of somebody else's project"),
    ("deploy", "putting the code somewhere it actually runs for real users"),
    ("rollback", "putting yesterday's working version back after a bad deploy"),
    ("build", "turning source code into the thing that runs"),
    ("environment variable", "a setting passed in from outside so secrets stay out of the code"),
    ("secret", "a password or key the code needs but must never contain"),
    ("API", "an agreed way for two bits of software to ask each other for things"),
    ("endpoint", "one specific address on an API that does one specific job"),
    ("webhook", "the other way round: they call you the moment something happens"),
    ("request and response", "the ask and the answer, and why the shape of both matters"),
    ("JSON", "the plain text format nearly everything uses to pass data about"),
    ("HTTP status code", "the three digit number that tells you how it went"),
    ("rate limit", "the cap on how often you are allowed to ask"),
    ("schema", "the agreed shape of your data before anyone puts anything in it"),
    ("database", "the filing system that survives a restart"),
    ("table and row", "the spreadsheet comparison, and where it breaks down"),
    ("index", "the reason a search is instant instead of slow"),
    ("query", "the question you ask the database"),
    ("migration", "changing the shape of live data without losing any of it"),
    ("backup", "the copy you will need on the worst day of the year"),
    ("cache", "keeping the answer handy so you do not do the work twice"),
    ("server", "a computer that never sleeps and never has a monitor"),
    ("client", "whatever is asking: a phone, a browser, another service"),
    ("frontend", "the part people see and press"),
    ("backend", "the part that does the work and holds the data"),
    ("framework", "a set of decisions already made for you"),
    ("library", "someone else's code you borrow for one job"),
    ("dependency", "the code your code cannot run without"),
    ("package manager", "the merchant that fetches and versions those dependencies"),
    ("container", "your app plus everything it needs, boxed so it runs anywhere"),
    ("runtime", "the thing that actually executes your code"),
    ("logs", "the running commentary you will be glad of at midnight"),
    ("exception", "an error the code did not expect and could not handle"),
    ("debugging", "narrowing down where reality stopped matching your assumption"),
    ("unit test", "a small automatic check that one piece still behaves"),
    ("staging", "a full copy of live where you break things on purpose"),
    ("production", "the real thing, with real users, where mistakes cost money"),
    ("CI/CD", "the robot that builds, checks and ships every change"),
    ("feature flag", "a switch that turns new work on for some people only"),
    ("technical debt", "the shortcut you took, and the interest it charges later"),
    ("refactor", "improving the inside without changing what it does outside"),
    ("MVP", "the smallest version worth putting in front of someone"),
    ("latency", "the wait between asking and getting"),
    ("uptime", "the percentage of the year the thing is actually working"),
    ("cron job", "a task that runs on a timetable without anyone pressing anything"),
    ("queue", "work parked in a line so a busy moment does not sink you"),
    ("authentication", "proving who you are"),
    ("authorisation", "what you are allowed to do once you are in"),
    ("token", "a temporary pass instead of handing over your password"),
    ("encryption", "scrambling data so only the right person can read it"),
    ("hashing", "a one-way fingerprint, which is why nobody can post you your password"),
    ("DNS", "the address book that turns a domain name into a machine"),
    ("SSL certificate", "the padlock, and what it does and does not promise"),
    ("agent", "a model given tools and allowed to decide when to use them"),
    ("prompt", "the instructions that set the job and the boundaries"),
    ("LLM", "a model that predicts the next word extremely well, and what that implies"),
    ("context window", "how much the model can hold in mind at once"),
    ("hallucination", "a confident answer with nothing behind it"),
    ("prompt injection", "hidden instructions in a web page trying to hijack your agent"),
    ("embedding", "turning meaning into numbers so similar things sit near each other"),
    ("vector database", "the filing cabinet for those numbers"),
    ("fine-tuning", "training a model further on your own examples"),
    ("open source", "code anyone can read, use and check"),
    ("licence", "the terms attached to that code, which do bind a business"),
    ("versioning", "why software goes 1.2.3 and what each number promises"),
]
