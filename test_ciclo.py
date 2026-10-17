"""Teste de ponta a ponta (banco local temporário). Executar: python test_ciclo.py"""
import contextlib
import io
import os
import tempfile

os.environ["BACKEND"] = "sqlite"
os.environ["CHARGEGRID_DB"] = os.path.join(tempfile.mkdtemp(), "teste.db")

import banco  # noqa: E402
import simulador  # noqa: E402

simulador.preparar()
import executor_comandos  # noqa: E402
import gerenciamento_demanda  # noqa: E402

db = banco.conectar()


def silencioso(fn):
    with contextlib.redirect_stdout(io.StringIO()):
        fn()


def potencias():
    return {c["id"]: c["potencia_kw"] for c in db.tabela("carregadores")}


def test_comandos_nao_duplicam_e_ciclo_atualiza_carregadores():
    assert potencias() == {1: 150, 2: 150, 3: 150, 4: 150}

    silencioso(gerenciamento_demanda.main)
    silencioso(gerenciamento_demanda.main)  # 2ª rodada sem executar: não pode duplicar
    pendentes = db.comandos_pendentes()
    assert len(pendentes) == 2, pendentes
    tipos = {c["carregador_id"]: c["tipo_comando"] for c in pendentes}
    assert tipos == {2: "REDUZIR", 1: "AUMENTAR"}  # o carregador 4 (livre) não é reduzido

    silencioso(executor_comandos.main)
    assert potencias() == {1: 200, 2: 100, 3: 150, 4: 150}
    assert db.comandos_pendentes() == []
    executados = [c for c in db.tabela("comandos_de_automacao") if c["executado"]]
    assert len(executados) == 2 and all(c["executado_em"] for c in executados)


def test_integridade_referencial():
    import sqlite3
    try:
        db.con.execute("INSERT INTO carregadores (id_estacao, status, potencia_kw) VALUES (999, 'Livre', 50)")
        raise AssertionError("FK não foi aplicada")
    except sqlite3.IntegrityError:
        pass


if __name__ == "__main__":
    test_comandos_nao_duplicam_e_ciclo_atualiza_carregadores(); print("OK  ciclo completo")
    test_integridade_referencial(); print("OK  chaves estrangeiras")
    print("\nTestes de integração passaram.")
