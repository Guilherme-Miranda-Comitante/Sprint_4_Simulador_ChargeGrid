import banco
import regras

db = banco.conectar()


def analisar_estado(estado, hora):
    print("\n==============================")
    print(f"Estado energético ID: {estado['id']}")
    print(f"Estação: {estado['estacao_id']}")
    print(f"Energia solar: {estado['energia_solar_kW']} kW")
    print(f"Energia da rede: {estado['energia_rede_kw']} kW")
    print(f"Demanda: {estado['demanda_kw']} kW")
    print(f"Potência disponível: {estado['potencia_disponivel_kw']} kW")
    print(f"Bateria: {estado['bateria_percentual']}%")
    print(f"Status: {estado['status_gerenciamento']}")

    carregadores = db.carregadores(estado["estacao_id"])
    print("\nCarregadores encontrados:")
    for carregador in carregadores:
        print(carregador)

    # A decisão vem do módulo de regras (lógica pura e testável)
    decisao = regras.decidir(estado, carregadores, hora)

    print(f"\nFaixa tarifária: {decisao['faixa']} ({regras.reais(regras.TARIFAS[decisao['faixa']])}/kWh)")
    print(f"Situação: {decisao['situacao']}")
    print(f"Bateria: {decisao['bateria_acao']}")

    if decisao["recomendacao"]:
        print(f"RECOMENDAÇÃO: {decisao['recomendacao']}")

    comando = decisao["comando"]
    if comando is None:
        print(f"\nDECISÃO: MANTER ({decisao['mensagem']})")
        return

    print(f"\nDECISÃO: {comando['tipo_comando']}")
    print(f"Carregador escolhido: {comando['carregador_id']}")

    if db.tem_comando_pendente(comando["carregador_id"]):
        print("Já existe um comando pendente para este carregador.")
        print("Nenhum novo comando será criado.")
        return

    print(
        f"Potência: {comando['potencia_anterior_kw']} → "
        f"{comando['potencia_nova_kw']} kW"
    )
    criado = db.criar_comando(comando)
    print("\nComando criado:")
    print(criado)


def main():
    print("================================")
    print("     CHARGEGRID INTELLIGENCE")
    print("     AUTOMAÇÃO ENERGÉTICA")
    print("================================")

    hora = regras.hora_atual()
    print(f"\nBackend de dados: {db.nome}")
    print(f"Hora atual (São Paulo): {hora}h")

    estados = db.estados()
    print(f"Estados encontrados: {len(estados)}")

    for estado in estados:
        analisar_estado(estado, hora)


if __name__ == "__main__":
    main()
