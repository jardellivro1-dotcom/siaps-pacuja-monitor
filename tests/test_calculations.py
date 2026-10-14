import unittest

from siaps.calculations import (
    INDICADORES_PESOS,
    calcular_nota_componente_3,
    classificar_componente_2,
    classificar_componente_3,
)


class TestMetodologiaNT82026(unittest.TestCase):
    def test_limites_componente_2(self):
        # Componente II: Ótimo > 8.5; Bom >= 7 e <= 8.5; Suficiente >= 5 e < 7; Regular < 5
        self.assertEqual(classificar_componente_2(8.51), "Ótimo")
        self.assertEqual(classificar_componente_2(8.5), "Bom")
        self.assertEqual(classificar_componente_2(7.0), "Bom")
        self.assertEqual(classificar_componente_2(6.99), "Suficiente")
        self.assertEqual(classificar_componente_2(5.0), "Suficiente")
        self.assertEqual(classificar_componente_2(4.99), "Regular")
        self.assertEqual(classificar_componente_2(0.0), "Regular")
        self.assertEqual(classificar_componente_2(None), "Indisponível")

    def test_limites_componente_3(self):
        # Componente III: Ótimo > 7.5; Bom >= 5 e <= 7.5; Suficiente > 2.5 e < 5; Regular <= 2.5
        self.assertEqual(classificar_componente_3(10.0), "Ótimo")
        self.assertEqual(classificar_componente_3(7.51), "Ótimo")
        self.assertEqual(classificar_componente_3(7.5), "Bom")
        self.assertEqual(classificar_componente_3(5.0), "Bom")
        self.assertEqual(classificar_componente_3(4.99), "Suficiente")
        self.assertEqual(classificar_componente_3(2.51), "Suficiente")
        self.assertEqual(classificar_componente_3(2.5), "Regular")
        self.assertEqual(classificar_componente_3(1.0), "Regular")
        self.assertEqual(classificar_componente_3(None), "Indisponível")

    def test_pesos_esf_totalizam_10(self):
        # C1 (1), C2 (2), C3 (2), C4 (1), C5 (1), C6 (1), C7 (2)
        esf_pesos = INDICADORES_PESOS["eSF"]
        total = sum(meta["peso"] for meta in esf_pesos.values())
        self.assertEqual(total, 10)

    def test_pesos_esb_totalizam_10(self):
        # B1 (2), B2 (2), B3 (2), B4 (1), B5 (2), B6 (1)
        esb_pesos = INDICADORES_PESOS["eSB"]
        total = sum(meta["peso"] for meta in esb_pesos.values())
        self.assertEqual(total, 10)

    def test_pesos_emulti_totalizam_10(self):
        # M1 (6), M2 (4)
        emulti_pesos = INDICADORES_PESOS["eMulti"]
        total = sum(meta["peso"] for meta in emulti_pesos.values())
        self.assertEqual(total, 10)

    def test_calculo_esf_todos_otimos(self):
        # Todos conceitos Ótimo (1.00) => nota 10.00 => Ótimo
        conceitos = {f"C{i}": "Ótimo" for i in range(1, 8)}
        res = calcular_nota_componente_3("eSF", conceitos)
        self.assertTrue(res.is_completo)
        self.assertEqual(res.nota, 10.0)
        self.assertEqual(res.classificacao, "Ótimo")

    def test_calculo_esf_todos_regulares(self):
        # Todos conceitos Regular (0.25) => nota 2.50 => Regular
        conceitos = {f"C{i}": "Regular" for i in range(1, 8)}
        res = calcular_nota_componente_3("eSF", conceitos)
        self.assertTrue(res.is_completo)
        self.assertEqual(res.nota, 2.5)
        self.assertEqual(res.classificacao, "Regular")

    def test_calculo_esf_dados_incompletos(self):
        # Faltando C2 e C7
        conceitos = {"C1": "Bom", "C3": "Bom", "C4": "Ótimo", "C5": "Bom", "C6": "Bom"}
        res = calcular_nota_componente_3("eSF", conceitos)
        self.assertFalse(res.is_completo)
        self.assertEqual(res.classificacao, "Incompleto")
        self.assertIn("C2", res.motivo_incompleto)
        self.assertIn("C7", res.motivo_incompleto)

    def test_exclusao_eapp_ecr_esfr_da_nt8_2026(self):
        # Regra 8 do AGENTS.md: Não aplique NT 8/2026 a eAPP, eCR ou eSFR
        for excluido in ["eAPP", "eCR", "eSFR"]:
            res = calcular_nota_componente_3(excluido, {})
            self.assertFalse(res.is_completo)
            self.assertEqual(res.classificacao, "Não aplicável")
            self.assertIn("não se aplica", res.motivo_incompleto)


if __name__ == "__main__":
    unittest.main()
