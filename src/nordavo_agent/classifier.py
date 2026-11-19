from __future__ import annotations

import re
import unicodedata

from .models import Category, Decision, Language, Ticket

WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)

LANGUAGE_MARKERS: dict[Language, frozenset[str]] = {
    "nl": frozenset(
        "ik mijn mij we wij ons onze het een de het is zijn heb heeft kan kunnen "
        "hoe waar waarom graag niet werkt toevoegen medewerker rooster factuur "
        "abonnement wachtwoord vestiging ruil aanmelden opzeggen wat kost voor "
        "hoeveel medewerkers vanavond onderhoud gepland btw prijs diensten".split()
    ),
    "en": frozenset(
        "i my me we our the a an is are have has can how where why please not "
        "working add employee schedule invoice subscription password location "
        "cancel what cost many staff crashes crash other publish visible next "
        "week".split()
    ),
    "de": frozenset(
        "ich mein meine wir unser der die das ein eine ist sind habe hat kann "
        "wie wo warum bitte nicht funktioniert hinzufügen mitarbeiter schicht "
        "rechnung passwort kündigen was kostet wieviel mitarbeiter wartung "
        "geplant".split()
    ),
}

HANDOFF_TERMS = (
    r"\b(refund|money back|geld terug|terugkrijgen|terugbetaling|terugstorten|restitutie|chargeback|terugboeking|"
    r"disputed charge|betwiste betaling|onterecht betaald|dubbel betaald|"
    r"charged twice|double charged|twice charged|"
    r"cancell?ation|cancel|annulering|opzeggen|opzegging|contractwijziging|"
    r"contract aanpassen|contract change|change contract|contract wijzigen|"
    r"abonnement wijzigen|abonnement aanpassen|upgrade|downgrade|"
    r"tarifwechsel|vertrag andern|vertrag ändern|kündigung|kundigung|"
    r"gdpr request|avg verzoek|avg request|persoonsgegevens|personal data|personenbezogene daten|"
    r"inzageverzoek|data access request|right to access my data|"
    r"delete my data|data verwijderen|gegevens verwijderen|"
    r"beveiligingsincident|gehackt|hacked|phishing|wachtwoord gestolen|password stolen|"
    r"unauthorized access|unauthorised access|suspicious login|data breach|datalek|security incident|"
    r"juridische stappen|rechtliche schritte|advocaat|lawyer|attorney|legal threat|"
    r"legal action|take you to court|sue( you)?|rechtszaak|rechtbank|klaag .* aan|"
    r"opstappen|overstappen naar|we vertrekken|ik vertrek|leave roosterly|"
    r"leaving roosterly|stoppen met roosterly|stop using roosterly|we are leaving|i am leaving|"
    r"we will leave|i will leave|considering leaving|thinking of leaving|"
    r"switch to another provider|move to another provider|ik wil vertrekken|we stappen over)\b"
)
SPAM_TERMS = re.compile(
    r"\b(buy now|casino|crypto giveaway|crypto fund|crypto investment|"
    r"investment opportunity|verdubbel je geld|double your money|free prize|"
    r"click here to claim|seo services|viagra|advertisement)\b",
    re.IGNORECASE,
)

FAQ_INTENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("password", ("wachtwoord", "password", "forgot password", "passwort", "inloggen", "login")),
    ("employee", ("medewerker toevoegen", "nieuwe medewerker", "new employee", "add employee", "uitnodigen", "mitarbeiter hinzufügen", "neue mitarbeiter")),
    ("shift_swap", ("ruil", "shift swap", "shifts ruilen", "dienst ruilen", "swap shift", "schicht tauschen", "dienst tauschen")),
    ("payroll", ("nmbrs", "loket.nl", "afas", "salaris", "payroll", "loonstrook", "csv export", "lohnabrechnung")),
    ("plans", ("basis", "plus", "prijzen", "price", "pricing", "kosten", "cost", "abonnement", "upgrade", "preise", "tarif", "kostet")),
    ("invoice", ("factuur", "facturen", "invoice", "invoices", "btw-nummer", "vat number", "rechnung", "rechnungen", "mehrwertsteuer")),
    ("locations", ("vestiging", "vestigingen", "locatie", "locations", "location", "standort", "standorte")),
    ("languages", ("taal", "talen", "language", "languages", "duits", "german", "sprache", "sprachen")),
    ("data_location", ("gegevens opgeslagen", "data stored", "waar staat mijn data", "frankfurt", "avg agreement", "daten gespeichert")),
    ("feature_idea", (
        "idee", "ideeën", "feature request", "functie toevoegen", "roadmap",
        "suggestie", "vorschlag", "featurewunsch", "koppeling met",
        "integratie met", "integration with", "calendar sync", "sync with",
        "would like to see", "could you add", "can you add",
    )),
    ("outage", ("storing", "uitval", "outage", "maintenance", "onderhoud", "statuspagina", "störung", "ausfall", "wartung")),
    ("mobile", ("ios", "android", "app requirements", "systeemvereisten", "locatie toestemming", "location permission", "systemanforderungen")),
)

FAQ_ANSWERS: dict[Language, dict[str, str]] = {
    "nl": {
        "password": "Ga naar app.roosterly.nl/login, kies ‘Wachtwoord vergeten’ en vul je e-mailadres in. De link is 60 minuten geldig. Geen e-mail binnen 10 minuten? Controleer je spammap.",
        "employee": "Ga naar Team → Medewerker toevoegen, vul naam, e-mailadres en contracturen in en kies Uitnodigen. De medewerker ontvangt een e-mail om de app te installeren. Je betaalt alleen voor actieve medewerkers.",
        "shift_swap": "Open de dienst in de app en tik op ‘Ruil aanbieden’. Collega’s met dezelfde rol kunnen de ruil accepteren. De manager keurt dit standaard goed via Rooster → Verzoeken; dit kun je aanpassen onder Instellingen → Rooster.",
        "payroll": "Goedgekeurde uren kun je exporteren naar Nmbrs, Loket.nl, AFAS of als CSV. Stel dit in via Instellingen → Koppelingen → Salaris. Exports lopen per week, vier weken of maand. De Nmbrs-, Loket.nl- en AFAS-koppelingen zijn onderdeel van Plus.",
        "plans": "Basis kost €4 per actieve medewerker per maand en omvat één locatie. Plus kost €6 per actieve medewerker per maand en omvat onbeperkte locaties, API-toegang en payrollkoppelingen. Prijzen zijn exclusief btw. Je kunt upgraden via Instellingen → Abonnement; de nieuwe prijs geldt vanaf de volgende factuur.",
        "invoice": "Facturen worden op de eerste dag van de maand gemaild en staan onder Instellingen → Abonnement → Facturen. Bedrijfsnaam, adres of btw-nummer voor toekomstige facturen wijzig je onder Instellingen → Bedrijfsgegevens.",
        "locations": "Locaties zijn inbegrepen bij Plus. Voeg een locatie toe via Instellingen → Vestigingen → Nieuwe vestiging. Medewerkers kunnen aan meerdere locaties gekoppeld worden.",
        "languages": "De webapp en mobiele app zijn beschikbaar in het Nederlands, Engels en Duits. Iedere gebruiker kiest de taal onder Profiel → Taal.",
        "data_location": "Alle gegevens worden opgeslagen in de EU (Frankfurt, Duitsland) en verwerkt onder een verwerkersovereenkomst. Je kunt die downloaden via Instellingen → Juridisch.",
        "feature_idea": "Ideeën zijn welkom. Feature requests staan op roadmap.roosterly.nl, waar je erop kunt stemmen. Voor individuele ideeën kunnen we geen leverdatum beloven.",
        "outage": "Actuele storingen en gepland onderhoud staan op status.roosterly.nl.",
        "mobile": "De app werkt op iOS 16 en hoger en Android 10 en hoger. Voor inklokken met locatie moet locatietoestemming voor de app aanstaan.",
    },
    "en": {
        "password": "Go to app.roosterly.nl/login, choose ‘Wachtwoord vergeten’ (Forgot password), and enter your email. The link is valid for 60 minutes. If no email arrives within 10 minutes, check spam.",
        "employee": "Go to Team → Medewerker toevoegen (Add employee), enter the name, email, and contract hours, then choose Uitnodigen (Invite). The employee receives an email to install the app. Only active employees are billed.",
        "shift_swap": "Open the shift in the app and tap ‘Ruil aanbieden’ (Offer swap). Colleagues with the same role can accept. A manager approves under Rooster → Verzoeken (Rota → Requests) by default; this can be changed under Instellingen → Rooster (Settings → Rota).",
        "payroll": "Approved hours can be exported to Nmbrs, Loket.nl, AFAS, or CSV. Configure this under Instellingen → Koppelingen → Salaris (Settings → Integrations → Payroll). Exports run weekly, every four weeks, or monthly. The three named integrations require Plus.",
        "plans": "Basis costs €4 per active employee per month for one location. Plus costs €6 per active employee per month and includes unlimited locations, API access, and payroll integrations. Prices exclude VAT. Upgrade under Instellingen → Abonnement (Settings → Subscription); the new price starts with the next invoice.",
        "invoice": "Invoices are emailed on the first of each month and are available under Instellingen → Abonnement → Facturen (Settings → Subscription → Invoices). Change the company name, address, or VAT number for future invoices under Instellingen → Bedrijfsgegevens (Settings → Company details).",
        "locations": "Locations are included in Plus. Add one under Instellingen → Vestigingen → Nieuwe vestiging (Settings → Locations → New location). Employees can be linked to multiple locations.",
        "languages": "The web and mobile apps are available in Dutch, English, and German. Each user chooses a language under Profiel → Taal (Profile → Language).",
        "data_location": "All data is stored in the EU (Frankfurt, Germany) and processed under a data processing agreement, available under Instellingen → Juridisch (Settings → Legal).",
        "feature_idea": "Feature requests are listed at roadmap.roosterly.nl, where you can vote. We cannot promise a delivery date for an individual idea.",
        "outage": "Current outages and planned maintenance are listed at status.roosterly.nl.",
        "mobile": "The app works on iOS 16 and later and Android 10 and later. Location permission is required for location-based clock-in.",
    },
    "de": {
        "password": "Gehen Sie zu app.roosterly.nl/login, wählen Sie „Wachtwoord vergeten“ (Passwort vergessen) und geben Sie Ihre E-Mail-Adresse ein. Der Link ist 60 Minuten gültig. Wenn innerhalb von 10 Minuten keine E-Mail ankommt, prüfen Sie bitte den Spam-Ordner.",
        "employee": "Gehen Sie zu Team → Medewerker toevoegen (Mitarbeiter hinzufügen), geben Sie Name, E-Mail-Adresse und Vertragsstunden ein und wählen Sie Uitnodigen (Einladen). Der Mitarbeiter erhält eine E-Mail zur Installation der App. Berechnet werden nur aktive Mitarbeiter.",
        "shift_swap": "Öffnen Sie die Schicht in der App und tippen Sie auf „Ruil aanbieden“ (Tausch anbieten). Kollegen mit derselben Rolle können den Tausch annehmen. Standardmäßig genehmigt ein Manager unter Rooster → Verzoeken (Dienstplan → Anfragen); dies lässt sich unter Instellingen → Rooster (Einstellungen → Dienstplan) ändern.",
        "payroll": "Genehmigte Stunden können nach Nmbrs, Loket.nl, AFAS oder als CSV exportiert werden. Richten Sie dies unter Instellingen → Koppelingen → Salaris (Einstellungen → Integrationen → Lohnabrechnung) ein. Exporte erfolgen wöchentlich, alle vier Wochen oder monatlich. Die drei genannten Integrationen erfordern Plus.",
        "plans": "Basis kostet 4 € pro aktivem Mitarbeiter und Monat für einen Standort. Plus kostet 6 € pro aktivem Mitarbeiter und Monat und umfasst unbegrenzte Standorte, API-Zugang und Lohnabrechnungsintegrationen. Die Preise verstehen sich ohne MwSt. Ein Upgrade ist unter Instellingen → Abonnement (Einstellungen → Abonnement) möglich; der neue Preis gilt ab der nächsten Rechnung.",
        "invoice": "Rechnungen werden am ersten Tag jedes Monats per E-Mail gesendet und sind unter Instellingen → Abonnement → Facturen (Einstellungen → Abonnement → Rechnungen) verfügbar. Firmenname, Adresse oder Umsatzsteuer-ID für künftige Rechnungen ändern Sie unter Instellingen → Bedrijfsgegevens (Einstellungen → Unternehmensdaten).",
        "locations": "Standorte sind in Plus enthalten. Fügen Sie einen Standort unter Instellingen → Vestigingen → Nieuwe vestiging (Einstellungen → Standorte → Neuer Standort) hinzu. Mitarbeiter können mehreren Standorten zugeordnet werden.",
        "languages": "Die Web- und Mobil-Apps sind auf Niederländisch, Englisch und Deutsch verfügbar. Jeder Benutzer wählt die Sprache unter Profiel → Taal (Profil → Sprache).",
        "data_location": "Alle Daten werden in der EU (Frankfurt, Deutschland) gespeichert und gemäß einer Auftragsverarbeitungsvereinbarung verarbeitet. Diese finden Sie unter Instellingen → Juridisch (Einstellungen → Rechtliches).",
        "feature_idea": "Feature-Wünsche werden unter roadmap.roosterly.nl veröffentlicht und können dort bewertet werden. Für einzelne Ideen können wir keinen Liefertermin zusagen.",
        "outage": "Aktuelle Ausfälle und geplante Wartungsarbeiten finden Sie unter status.roosterly.nl.",
        "mobile": "Die App funktioniert ab iOS 16 und Android 10. Für die standortbasierte Zeiterfassung ist die Standortberechtigung der App erforderlich.",
    },
}

FAQ_REFERENCES = {
    "password": "F01",
    "employee": "F02",
    "shift_swap": "F03",
    "payroll": "F04",
    "plans": "F05",
    "invoice": "F06",
    "locations": "F07",
    "languages": "F08",
    "data_location": "F09",
    "feature_idea": "F10",
    "outage": "F11",
    "mobile": "F12",
}


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def detect_language(text: str) -> tuple[Language, float]:
    words = set(WORD_RE.findall(_normalize(text)))
    scores = {
        language: len(words.intersection(markers))
        for language, markers in LANGUAGE_MARKERS.items()
    }
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if ranked[0][1] == 0:
        return "nl", 0.30
    language, score = ranked[0]
    runner_up = ranked[1][1]
    confidence = min(0.98, 0.55 + (score - runner_up) * 0.12 + score * 0.04)
    return language, confidence


def _category(text: str, intent: str | None) -> Category:
    normalized = _normalize(text)
    if re.search(
        r"\b(bug|fout|storing|werkt niet|does not work|not working|error|fehler|"
        r"funktioniert nicht|crash|crashes|crashing|something went wrong|"
        r"can't publish|cannot publish|not visible|niet zichtbaar)\b",
        normalized,
    ):
        return "bug"
    if re.search(r"\b(factuur|facturen|invoice|invoices|rechnung|zahlungen|zahlung|billing|prijs|prijzen|kosten|refund|money back|geld terug|terugkrijgen|terugbetaling|terugboeking|chargeback)\b", normalized):
        return "billing"
    if intent == "feature_idea":
        return "feature_request"
    if intent is not None or re.search(r"\b(vraag|hoe|waar|question|how|where|why|warum|wie)\b", normalized):
        return "question"
    return "other"


def _priority(text: str, category: Category) -> str:
    normalized = _normalize(text)
    if re.search(
        r"\b(veiligheidsincident|gehackt|hacked|phishing|wachtwoord gestolen|"
        r"password stolen|unauthorized access|unauthorised access|suspicious login|"
        r"data breach|datalek|security incident|juridische stappen|"
        r"rechtliche schritte|advocaat|lawyer|legal action|sue you)\b",
        normalized,
    ):
        return "P1"
    many_users_affected = re.search(
        r"\b(nobody|niemand|everyone|everybody|iedereen|all users|all staff|"
        r"all employees|alle gebruikers|alle medewerkers|hele team|hele locatie|"
        r"all mitarbeiter|gesamte team|ganzes team)\b",
        normalized,
    )
    blocking = re.search(
        r"\b(blocked|geblokkeerd|cannot|can't|unable|kan niet|kunnen niet|"
        r"kann nicht|konnen nicht|not visible|niet zichtbaar|not working|"
        r"werkt niet|cannot publish|can't publish)\b",
        normalized,
    )
    if many_users_affected and blocking:
        return "P1"
    if re.search(
        r"\b(blocked|geblokkeerd|kan niet|kunnen niet|cannot|can't|unable to|"
        r"locked out|kann nicht|konnen nicht|kan niet inklokken|cannot clock in|"
        r"not visible|niet zichtbaar|can't publish|cannot publish|unable to publish)\b",
        normalized,
    ):
        return "P2"
    if re.search(
        r"\b(gdpr request|avg verzoek|avg request|persoonsgegevens|personal data|"
        r"personenbezogene daten|inzageverzoek|data access request|"
        r"right to access my data|delete my data|data verwijderen|gegevens verwijderen)\b",
        normalized,
    ):
        return "P2"
    if re.search(
        r"\b(refund|money back|geld terug|terugbetaling|terugkrijgen|terugstorten|"
        r"restitutie|chargeback|disputed charge|betwiste betaling|overcharged|charged twice|double charged|"
        r"betaling mislukt|payment failed|payment declined|incorrect charge|"
        r"contractwijziging|contract aanpassen|contract wijzigen|contract change|"
        r"cancellation|annulering|opzeggen|opzegging)\b",
        normalized,
    ):
        return "P2"
    if category == "bug":
        return "P3"
    return "P4"


def _plan_reply(text: str, language: Language) -> str:
    reply = FAQ_ANSWERS[language]["plans"]
    normalized = _normalize(text)
    if "plus" in normalized:
        monthly_price = 6
    elif "basis" in normalized:
        monthly_price = 4
    else:
        return reply

    count_match = re.search(
        r"\b(\d+)\s+(?:actieve\s+)?medewerkers?\b|"
        r"\b(\d+)\s+(?:active\s+)?employees?\b|"
        r"\b(\d+)\s+(?:aktive\s+)?mitarbeiter\b",
        normalized,
    )
    if count_match is None:
        return reply
    employee_count = int(next(group for group in count_match.groups() if group))
    monthly_total = employee_count * monthly_price
    if language == "nl":
        addition = (
            f" Als alle {employee_count} medewerkers actief zijn, is dat "
            f"€{monthly_total} per maand exclusief btw."
        )
    elif language == "de":
        addition = (
            f" Wenn alle {employee_count} Mitarbeiter aktiv sind, sind das "
            f"{monthly_total} € pro Monat zzgl. MwSt."
        )
    else:
        addition = (
            f" If all {employee_count} employees are active, that is "
            f"€{monthly_total} per month, excluding VAT."
        )
    return reply + addition


def _find_faq_intent(text: str) -> str | None:
    normalized = _normalize(text)
    for intent, phrases in FAQ_INTENTS:
        if any(_normalize(phrase) in normalized for phrase in phrases):
            return intent
    return None


def reply_audit() -> list[dict[str, str]]:
    return [
        {
            "faq": faq_id,
            "intent": intent,
            "english_reference": FAQ_ANSWERS["en"][intent],
            "dutch_reply": FAQ_ANSWERS["nl"][intent],
            "german_reply": FAQ_ANSWERS["de"][intent],
        }
        for intent, faq_id in FAQ_REFERENCES.items()
    ]


def classify(ticket: Ticket) -> Decision:
    text = f"{ticket.subject}\n{ticket.body}".strip()
    language, language_confidence = detect_language(text)
    normalized = _normalize(text)
    category_hint = _find_faq_intent(text)
    category = _category(text, category_hint)
    priority = _priority(text, category)

    if not text:
        return Decision(
            language="nl",
            category="other",
            priority="P4",
            action="close",
            reason="Category other, priority P4, close: the ticket has no subject or message content, so there is nothing to answer.",
            confidence=0.99,
        )
    if SPAM_TERMS.search(text):
        return Decision(
            language=language,
            category="other",
            priority="P4",
            action="close",
            reason="Category other, priority P4, close: the message matches an obvious unsolicited-advertising pattern.",
            confidence=0.86,
        )

    mandatory_handoff = re.search(HANDOFF_TERMS, normalized) is not None
    intent = _find_faq_intent(text)
    if mandatory_handoff:
        reason = (
            f"Category {category}, priority {priority}, handoff: the message concerns a "
            "client-mandated human-only topic, so a support specialist must review it."
        )
        note = (
            "Please review this ticket under the mandatory handoff policy. Check the customer's request and "
            "account history before responding; do not repeat any payment details."
        )
        return Decision(
            language=language,
            category=category,
            priority=priority,
            action="handoff",
            reason=reason,
            confidence=max(0.90, language_confidence),
            handoff_note=note,
        )

    if language_confidence < 0.60:
        intent = None
    if intent is not None:
        reply = _plan_reply(text, language) if intent == "plans" else FAQ_ANSWERS[language][intent]
        return Decision(
            language=language,
            category=category,
            priority=priority,
            action="reply",
            reason=(
                f"Category {category}, priority {priority}, reply: this is a supported "
                f"help-centre topic ({intent}); the response uses only the supplied FAQ information."
            ),
            confidence=min(0.95, max(0.65, 0.70 + (language_confidence - 0.5) / 2)),
            draft_reply=reply,
        )

    if re.search(r"^\s*(hi|hello|hallo|hoi|goedemorgen|goedemiddag|goedenavond)[!. ]*$", text, re.IGNORECASE):
        return Decision(
            language=language,
            category="other",
            priority="P4",
            action="reply",
            reason="Category other, priority P4, reply: the ticket is only a greeting and does not request unsupported product information.",
            confidence=0.72,
            draft_reply={
                "nl": "Hoi! Waarmee kan ik je helpen?",
                "en": "Hello! How can I help you?",
                "de": "Hallo! Wie kann ich Ihnen helfen?",
            }[language],
        )

    return Decision(
        language=language,
        category=category,
        priority=priority,
        action="handoff",
        reason=(
            f"Category {category}, priority {priority}, handoff: the request is not clearly "
            "answered by the supplied help centre, so a human should review it."
        ),
        confidence=min(0.72, max(0.45, language_confidence)),
        handoff_note=(
            "Please review the customer's request and respond using approved product information. "
            "The automated agent could not match it to a supported help-centre answer."
        ),
    )
