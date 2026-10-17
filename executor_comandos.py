import banco

db = banco.conectar()


def executar_comando(comando):
    comando_id = comando["id"]
    carregador_id = comando["carregador_id"]
    nova_potencia = float(comando["potencia_nova_kw"])

    print("\n==============================")
    print(f"Executando comando: {comando_id}")
    print(f"Tipo: {comando['tipo_comando']}")
    print(f"Carregador: {carregador_id}")
    print(f"Potência: {comando['potencia_anterior_kw']} → {nova_potencia} kW")

    # 1. Atualiza o carregador
    db.atualizar_potencia(carregador_id, nova_potencia)

    # 2. Registra a execução (executado = true e data/hora)
    db.marcar_executado(comando_id)

    print("Comando executado com sucesso!")


def main():
    print("================================")
    print("     CHARGEGRID INTELLIGENCE")
    print("     EXECUTOR DE COMANDOS")
    print("================================")

    comandos = db.comandos_pendentes()
    print(f"\nComandos pendentes: {len(comandos)}")

    if not comandos:
        print("Nenhum comando pendente.")
        return

    for comando in comandos:
        executar_comando(comando)


if __name__ == "__main__":
    main()
