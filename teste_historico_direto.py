from adaptador_pi_af import carregar_historico_pi_point


df = carregar_historico_pi_point(
    servidor_pi="ce-srv11",
    nome_pi_point="IEE-TA1-DQO",
    inicio="*-365d",
    fim="*"
)

print(f"Registros: {len(df)}")
print(df)