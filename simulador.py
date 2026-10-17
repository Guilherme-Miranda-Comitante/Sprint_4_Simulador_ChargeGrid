"""
ChargeGrid Intelligence - Simulador de cenários (banco local SQLite).

  python simulador.py          -> recria o banco local com os 3 cenários de teste
  python simulador.py --demo   -> recria, roda o ciclo completo e mostra antes/depois

O simulador usa SEMPRE o banco local. Dados 100% simulados.
"""

import os
import sys

os.environ["BACKEND"] = "sqlite"

import banco  # noqa: E402

ESTACOES = [
    (1, "EV Charge - Paulista", "Av. Paulista, 1578"),
    (2, "EV Charge - Pinheiros", "R. dos Pinheiros, 840"),
    (3, "EV Charge - Vila Olímpia", "R. Funchal, 263"),
]

# estacao_id, solar, rede, demanda, disponivel, bateria %, status, descrição
CENARIOS = [
    (3, 8.5, 0.0, 5.5, 10.0, 70, "Normal", "Normal: demanda dentro da potência disponível"),
    (2, 3.0, 9.0, 12.0, 5.0, 50, "Demanda elevada", "Demanda elevada: acima da potência disponível"),
    (1, 15.0, 0.0, 5.0, 15.0, 60, "Energia solar disponível", "Solar excedente: geração acima da demanda"),
]

# id, estação, status, potência kW
CARREGADORES = [
    (1, 1, "Livre", 150),
    (2, 2, "Ocupado", 150),
    (3, 3, "Ocupado", 150),
    (4, 2, "Livre", 150),
]


def preparar():
    """Recria o banco local e insere estações, carregadores, cenários e sessões de exemplo."""
    db = banco.recriar_sqlite()
    con = db.con
    con.executemany("INSERT INTO estacoes (id, nome, endereco) VALUES (?, ?, ?)", ESTACOES)
    con.execute("INSERT INTO usuarios (id, nome) VALUES (1, 'Guilherme Miranda')")
    con.execute(
        "INSERT INTO veiculos (id, usuario_id, modelo, placa, capacidade_kwh) "
        "VALUES (1, 1, 'BYD Seal', 'ABC1D23', 75)"
    )
    con.executemany(
        "INSERT INTO tarifas (id, nome, preco_kwh) VALUES (?, ?, ?)",
        [(1, "Fora de pico", 0.65), (2, "Normal", 0.85), (3, "Pico", 1.20)],
    )
    con.executemany(
        "INSERT INTO carregadores (id, id_estacao, status, potencia_kw) VALUES (?, ?, ?, ?)",
        CARREGADORES,
    )
    con.executemany(
        "INSERT INTO estado_energetico (estacao_id, energia_solar_kW, energia_rede_kw, demanda_kw, "
        "potencia_disponivel_kw, bateria_percentual, status_gerenciamento) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [c[:7] for c in CENARIOS],
    )
    # Sessões de exemplo: custo = energia x tarifa da faixa horária
    con.executemany(
        "INSERT INTO sessoes_carregamento (estacao_id, carregador_id, usuario_id, veiculo_id, tarifa_id, "
        "tempo_inicial, tempo_final, energia_kWh, custo, status) VALUES (?, ?, 1, 1, ?, ?, ?, ?, ?, 'Concluída')",
        [
            (1, 1, 1, "2026-08-26 22:13:00", "2026-08-26 23:03:00", 2.2, round(2.2 * 0.65, 2)),
            (2, 2, 3, "2026-08-17 21:14:00", "2026-08-17 21:34:00", 0.8, round(0.8 * 1.20, 2)),
        ],
    )
    con.commit()
    return db


def _potencias():
    return {c["id"]: c["potencia_kw"] for c in banco.conectar().tabela("carregadores")}


def main():
    preparar()
    print("=" * 56)
    print("  CHARGEGRID INTELLIGENCE - SIMULADOR (banco local)")
    print("=" * 56)
    print("\nCenários carregados em estado_energetico:")
    for c in CENARIOS:
        print(f"  Estação {c[0]}: {c[7]}")
    print(f"\nArquivo do banco: {banco.CAMINHO_DB}")

    if "--demo" not in sys.argv:
        print("\nPróximo passo: python main.py")
        return

    antes = _potencias()
    import executor_comandos
    import gerenciamento_demanda

    gerenciamento_demanda.main()
    executor_comandos.main()
    depois = _potencias()

    print("\n" + "=" * 56)
    print("  RESUMO DO CICLO: COMANDOS REGISTRADOS")
    print("=" * 56)
    for c in banco.conectar().tabela("comandos_de_automacao"):
        print(
            f"  #{c['id']} {c['tipo_comando']:<8} carregador {c['carregador_id']}: "
            f"{c['potencia_anterior_kw']:.0f} -> {c['potencia_nova_kw']:.0f} kW | "
            f"{c['motivo']} | executado: {'sim' if c['executado'] else 'nao'}"
        )

    print("\n" + "=" * 56)
    print("  RESULTADO: POTÊNCIA DOS CARREGADORES (kW)")
    print("=" * 56)
    print(f"{'Carregador':<12}{'Antes':>8}{'Depois':>8}   Variação")
    for cid in sorted(antes):
        delta = depois[cid] - antes[cid]
        marca = f"{delta:+.0f} kW" if delta else "sem alteração"
        print(f"{cid:<12}{antes[cid]:>8.0f}{depois[cid]:>8.0f}   {marca}")


if __name__ == "__main__":
    main()
