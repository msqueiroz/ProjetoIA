from adaptador_ia import verificar_ollama


resultado = verificar_ollama()

print("Disponível:", resultado["disponivel"])
print("Modelos:", resultado["modelos"])
print("Erro:", resultado["erro"])