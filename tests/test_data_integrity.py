"""
Test d'intégrité des données d'apprentissage et de configuration Rasa (DSP).
Vérifie l'absence de fuite de données (Data Leakage) et la conformité du domaine.
"""

import os
import re
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def extract_nlu_examples(filepath):
    examples = set()
    if not os.path.exists(filepath):
        return examples
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if (
                line.startswith("- ")
                and not line.startswith("- intent:")
                and not line.startswith("- regex:")
                and not line.startswith("- lookup:")
                and not line.startswith("- synonym:")
            ):
                clean = line[2:].strip().lower()
                if clean:
                    examples.add(clean)
    return examples


class TestDataIntegrity(unittest.TestCase):

    def test_no_data_leakage_between_train_and_test(self):
        """Vérifie l'absence totale de phrases du jeu de test dans le jeu d'entraînement."""
        train_path = os.path.join(BASE_DIR, "data", "nlu", "nlu.yml")
        test_path = os.path.join(BASE_DIR, "tests", "test_nlu.yml")

        train_ex = extract_nlu_examples(train_path)
        test_ex = extract_nlu_examples(test_path)

        leakage = train_ex.intersection(test_ex)
        self.assertEqual(
            len(leakage),
            0,
            f"Fuite de données détectée ({len(leakage)} exemples communs) : {leakage}",
        )

    def test_domain_actions_exist_in_actions_py(self):
        """Vérifie que chaque action déclarée dans domain.yml est implémentée dans actions/actions.py."""
        domain_path = os.path.join(BASE_DIR, "intelligence", "domain.yml")
        actions_py_path = os.path.join(BASE_DIR, "actions", "actions.py")

        self.assertTrue(os.path.exists(domain_path))
        self.assertTrue(os.path.exists(actions_py_path))

        with open(actions_py_path, encoding="utf-8") as f:
            actions_code = f.read()

        # Extraction des noms d'actions déclarées dans domain.yml
        declared_actions = []
        in_actions_block = False
        with open(domain_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("actions:"):
                    in_actions_block = True
                    continue
                if in_actions_block:
                    if line.startswith("  - action_"):
                        action_name = line.strip().lstrip("-").strip()
                        declared_actions.append(action_name)
                    elif line and not line.startswith(" "):
                        break

        self.assertTrue(len(declared_actions) > 0, "Aucune action trouvée dans domain.yml")

        for act in declared_actions:
            self.assertIn(
                f'return "{act}"',
                actions_code,
                f"L'action déclarée '{act}' n'est pas implémentée dans actions/actions.py",
            )

    def test_faq_file_is_valid_json(self):
        """Vérifie que la FAQ des démarches est un JSON valide et bien structuré."""
        import json

        faq_path = os.path.join(BASE_DIR, "data", "faq", "faq_demarches.json")
        self.assertTrue(os.path.exists(faq_path), "Fichier faq_demarches.json absent")

        with open(faq_path, encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("categories", data)
        self.assertTrue(len(data["categories"]) >= 4)
        for cat in data["categories"]:
            self.assertIn("id", cat)
            self.assertIn("title_fr", cat)
            self.assertIn("title_bm", cat)
            self.assertIn("answer_fr", cat)
            self.assertIn("answer_bm", cat)


if __name__ == "__main__":
    unittest.main()
