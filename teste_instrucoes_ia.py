import unittest

from adaptador_ia import carregar_instrucao_base, _prompt_com_instrucao_base


class TestInstrucoesIA(unittest.TestCase):
    def test_instrucao_base_compartilhada(self) -> None:
        instrucao = carregar_instrucao_base()
        self.assertIn("MAR.IA", instrucao)
        self.assertIn("Não invente valores", instrucao)
        self.assertIn("somente leitura", instrucao)

    def test_prompt_copilot_recebe_instrucao_base(self) -> None:
        prompt = _prompt_com_instrucao_base("CASO DE TESTE")
        self.assertIn("INSTRUÇÕES GERAIS DO ASSISTENTE", prompt)
        self.assertIn("CASO DE TESTE", prompt)


if __name__ == "__main__":
    unittest.main()
