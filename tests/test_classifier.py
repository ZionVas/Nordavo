import unittest

from nordavo_agent.classifier import FAQ_ANSWERS, FAQ_REFERENCES, classify, detect_language, reply_audit
from nordavo_agent.models import Ticket


class ClassifierTests(unittest.TestCase):
    def classify(self, subject: str, body: str) -> object:
        return classify(Ticket(id="T1", subject=subject, body=body))

    def test_supported_dutch_faq_gets_dutch_reply(self) -> None:
        decision = self.classify("Nieuwe medewerker", "Hoe voeg ik een nieuwe medewerker toe?")
        self.assertEqual(decision.action, "reply")
        self.assertEqual(decision.language, "nl")
        self.assertIn("Team → Medewerker toevoegen", decision.draft_reply)

    def test_refund_is_mandatory_handoff_even_when_faq_related(self) -> None:
        decision = self.classify("Factuur", "Ik wil een terugbetaling van mijn factuur.")
        self.assertEqual(decision.action, "handoff")
        self.assertEqual(decision.category, "billing")
        self.assertEqual(decision.priority, "P2")
        self.assertIsNotNone(decision.handoff_note)

    def test_money_back_request_is_a_billing_handoff(self) -> None:
        decision = self.classify("Payment", "I want my money back.")
        self.assertEqual(decision.action, "handoff")
        self.assertEqual(decision.category, "billing")
        self.assertEqual(decision.priority, "P2")

    def test_security_and_legal_escalation_phrases_are_handed_off(self) -> None:
        security = self.classify("Login", "There was a suspicious login to my account.")
        legal = self.classify("Complaint", "I will take you to court.")
        self.assertEqual((security.action, security.priority), ("handoff", "P1"))
        self.assertEqual(legal.action, "handoff")

    def test_security_incident_is_p1_handoff(self) -> None:
        decision = self.classify("Account gehackt", "Mijn account is gehackt.")
        self.assertEqual(decision.action, "handoff")
        self.assertEqual(decision.priority, "P1")

    def test_personal_data_request_is_handed_off_but_data_location_question_is_answered(self) -> None:
        request = self.classify("AVG-verzoek", "Ik wil mijn persoonsgegevens laten verwijderen.")
        question = self.classify("Gegevens", "Waar worden mijn gegevens opgeslagen?")
        self.assertEqual(request.action, "handoff")
        self.assertEqual(request.priority, "P2")
        self.assertEqual(question.action, "reply")
        self.assertIn("Frankfurt", question.draft_reply)

    def test_contract_change_is_handed_off(self) -> None:
        decision = self.classify("Abonnement", "How do I upgrade to Plus?")
        self.assertEqual(decision.action, "handoff")

    def test_one_customer_blocked_is_p2(self) -> None:
        decision = self.classify("Inloggen", "Ik kan niet inloggen.")
        self.assertEqual(decision.priority, "P2")

    def test_many_users_blocked_is_p1_but_one_user_blocked_is_p2(self) -> None:
        one_user = self.classify("Login", "I am blocked from logging in.")
        many_users = self.classify("Login", "All staff are blocked from logging in.")
        self.assertEqual(one_user.priority, "P2")
        self.assertEqual(many_users.priority, "P1")

    def test_blank_ticket_is_closed(self) -> None:
        decision = self.classify("", "  ")
        self.assertEqual((decision.action, decision.category, decision.priority), ("close", "other", "P4"))

    def test_unsupported_request_is_handed_off(self) -> None:
        decision = self.classify("API werkt niet", "Onze API geeft een foutmelding.")
        self.assertEqual(decision.action, "handoff")
        self.assertEqual(decision.category, "bug")

    def test_supported_intent_uses_customer_language(self) -> None:
        decision = self.classify("Invoice question", "How do I download an invoice?")
        self.assertEqual(decision.action, "reply")
        self.assertEqual(decision.language, "en")
        self.assertIn("Invoices are emailed", decision.draft_reply)

    def test_supported_german_faq_gets_german_reply(self) -> None:
        decision = self.classify("Rechnung", "Wie kann ich meine Rechnung herunterladen?")
        self.assertEqual(decision.action, "reply")
        self.assertEqual(decision.language, "de")
        self.assertIn("Rechnungen werden", decision.draft_reply)

    def test_ios_requirement_question_is_classified_as_bug_and_answered(self) -> None:
        decision = self.classify(
            "App crashes",
            "The app crashes immediately on my iPhone 8 (iOS 15). Other staff are fine.",
        )
        self.assertEqual(decision.category, "bug")
        self.assertEqual(decision.priority, "P3")
        self.assertEqual(decision.action, "reply")
        self.assertIn("iOS 16", decision.draft_reply)

    def test_vat_number_change_is_a_low_urgency_invoice_question(self) -> None:
        decision = self.classify(
            "Btw-nummer",
            "Ons btw-nummer is veranderd. Kunnen jullie het nieuwe op onze facturen zetten?",
        )
        self.assertEqual(decision.category, "billing")
        self.assertEqual(decision.priority, "P4")
        self.assertEqual(decision.action, "reply")

    def test_calendar_integration_idea_is_answered_with_roadmap(self) -> None:
        decision = self.classify(
            "Google Agenda",
            "Graag een koppeling met Google Agenda voor de diensten.",
        )
        self.assertEqual(decision.category, "feature_request")
        self.assertEqual(decision.action, "reply")
        self.assertIn("roadmap.roosterly.nl", decision.draft_reply)

    def test_publish_failure_is_a_blocking_bug_handoff(self) -> None:
        decision = self.classify(
            "Can't publish rota",
            "When I click Publish I get 'Something went wrong'. Next week's rota is not visible for staff.",
        )
        self.assertEqual(decision.category, "bug")
        self.assertEqual(decision.priority, "P2")
        self.assertEqual(decision.action, "handoff")

    def test_plan_price_for_employee_count_is_calculated_from_faq_rate(self) -> None:
        decision = self.classify("Prijs Plus", "Wat kost Plus voor 25 medewerkers?")
        self.assertEqual(decision.category, "billing")
        self.assertEqual(decision.priority, "P4")
        self.assertEqual(decision.action, "reply")
        self.assertIn("€150 per maand", decision.draft_reply)
        self.assertIn("exclusief btw", decision.draft_reply)

    def test_crypto_investment_spam_is_closed(self) -> None:
        decision = self.classify(
            "Investeringskans",
            "Verdubbel je geld in 7 dagen met ons cryptofonds.",
        )
        self.assertEqual(decision.action, "close")
        self.assertEqual(decision.category, "other")
        self.assertEqual(decision.priority, "P4")

    def test_scheduled_maintenance_question_gets_status_page_reply(self) -> None:
        decision = self.classify("Onderhoud", "Is er vanavond onderhoud gepland?")
        self.assertEqual(decision.language, "nl")
        self.assertEqual(decision.category, "question")
        self.assertEqual(decision.priority, "P4")
        self.assertEqual(decision.action, "reply")
        self.assertIn("status.roosterly.nl", decision.draft_reply)

    def test_reason_explains_category_priority_and_action(self) -> None:
        decision = self.classify("Nieuwe medewerker", "Hoe voeg ik een nieuwe medewerker toe?")
        self.assertIn("question", decision.reason)
        self.assertIn("P4", decision.reason)
        self.assertIn("reply", decision.reason)

    def test_unrecognized_language_text_is_low_confidence(self) -> None:
        language, confidence = detect_language("???")
        self.assertEqual(language, "nl")
        self.assertLess(confidence, 0.6)

    def test_reply_audit_pairs_each_localized_template_with_english(self) -> None:
        audit = reply_audit()
        self.assertEqual(len(audit), 12)
        self.assertEqual({entry["intent"] for entry in audit}, set(FAQ_REFERENCES))
        for entry in audit:
            intent = entry["intent"]
            self.assertEqual(entry["faq"], FAQ_REFERENCES[intent])
            self.assertEqual(entry["english_reference"], FAQ_ANSWERS["en"][intent])
            self.assertEqual(entry["dutch_reply"], FAQ_ANSWERS["nl"][intent])
            self.assertEqual(entry["german_reply"], FAQ_ANSWERS["de"][intent])


if __name__ == "__main__":
    unittest.main()
