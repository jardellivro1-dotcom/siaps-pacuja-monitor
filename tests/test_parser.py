import unittest

from siaps.parser import ParseValidationError, normalize_float, normalize_int, parse_siaps_csv


class TestSiapsParser(unittest.TestCase):
    def test_reject_empty_csv(self):
        with self.assertRaises(ParseValidationError) as ctx:
            parse_siaps_csv("")
        self.assertIn("vazio", str(ctx.exception).lower())

    def test_reject_missing_institutional_header(self):
        invalid_content = "Coluna1;Coluna2\nValor1;Valor2\n"
        with self.assertRaises(ParseValidationError) as ctx:
            parse_siaps_csv(invalid_content)
        self.assertIn("institucional", str(ctx.exception).lower())

    def test_reject_wrong_territory(self):
        # Município diferente de Pacujá / CE
        csv_wrong_mun = """Ministério da Saúde - MS
Secretaria de Atenção Primária à Saúde - Saps
Sistema de Informação para a Atenção Primária à Saúde – Siaps
Dado gerado em: 10 de outubro de 2026 - 12:00h
Relatorio Publico - Teste
Dado Preliminar

Dados sociodemográficos:
UF: SP
Município: 355030 / SÃO PAULO

Quadrimestre/Ano;Estado;Código IBGE;Município;Classificação Final
2026Q1;SP;355030;São Paulo;Ótimo
"""
        with self.assertRaises(ParseValidationError) as ctx:
            parse_siaps_csv(csv_wrong_mun)
        self.assertIn("pacujá", str(ctx.exception).lower())

    def test_parse_valid_pacuja_csv(self):
        csv_valid = """Ministério da Saúde - MS
Secretaria de Atenção Primária à Saúde - Saps
Sistema de Informação para a Atenção Primária à Saúde – Siaps
Dado gerado em: 10 de outubro de 2026 - 12:00h
Relatorio Publico - Classificacao Geral dos Componentes
Dado Preliminar

Dados sociodemográficos:
UF: CE
Município: 230990 / PACUJÁ

Quadrimestre/Ano;Estado;Código IBGE;Município;Classificação Final;Vínculo e Acompanhamento Territorial -  Nº eSF
"2026Q1\t";"CE\t";"230990\t";"PACUJÁ\t";"Ótimo\t";"3\t"

Fonte: Sistema de Informação para a Atenção Primária à Saúde - SIAPS
"""
        res = parse_siaps_csv(csv_valid)
        self.assertEqual(res["report_type"], "geral_componentes")
        self.assertEqual(res["total_rows"], 1)
        row = res["rows"][0]
        self.assertEqual(row[0], "2026Q1")
        self.assertEqual(row[1], "CE")
        self.assertEqual(row[2], "230990")
        self.assertEqual(row[3], "PACUJÁ")
        self.assertEqual(row[4], "Ótimo")
        self.assertEqual(row[5], "3")

    def test_normalizers(self):
        self.assertEqual(normalize_int("42"), 42)
        self.assertEqual(normalize_int("42.0"), 42)
        self.assertIsNone(normalize_int("-"))
        self.assertIsNone(normalize_int(""))
        self.assertIsNone(normalize_int(None))

        self.assertEqual(normalize_float("100.0"), 100.0)
        self.assertEqual(normalize_float("33,33"), 33.33)
        self.assertIsNone(normalize_float("-"))
        self.assertIsNone(normalize_float(""))


if __name__ == "__main__":
    unittest.main()
