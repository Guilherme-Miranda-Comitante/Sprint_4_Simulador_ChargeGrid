import subprocess
import sys

import banco


def preparar_banco():
    """Valida a conexão e, no modo local, cria os cenários se o banco estiver vazio."""
    try:
        db = banco.conectar()
        vazio = not db.estados()
    except Exception as erro:  # credenciais ausentes, projeto pausado, sem internet...
        sys.exit(
            f"Não foi possível acessar o banco ({banco.BACKEND}): {erro}\n"
            "Dica: use o banco local com BACKEND=sqlite no .env (veja .env.example)."
        )

    if banco.BACKEND == "sqlite" and vazio:
        print("Banco local vazio. Criando os cenários de teste...")
        import simulador

        simulador.preparar()


def executar_script(nome_script):
    print("\n" + "=" * 50)
    print(f"EXECUTANDO: {nome_script}")
    print("=" * 50)

    resultado = subprocess.run([sys.executable, nome_script])

    if resultado.returncode != 0:
        print(f"\nErro ao executar {nome_script}")
        return False

    print(f"\n{nome_script} finalizado com sucesso.")
    return True


def main():
    print("=" * 50)
    print("       CHARGEGRID INTELLIGENCE")
    print("       SISTEMA DE AUTOMAÇÃO")
    print("=" * 50)
    print(f"\nBackend de dados: {banco.BACKEND}")

    preparar_banco()
    print("\nIniciando ciclo de gerenciamento energético...")

    # 1. Analisa os estados (regras.py) e cria os comandos
    if not executar_script("gerenciamento_demanda.py"):
        print("\nO processo foi interrompido.")
        return

    # 2. Executa os comandos criados e atualiza os carregadores
    if not executar_script("executor_comandos.py"):
        print("\nO processo foi interrompido.")
        return

    print("\n" + "=" * 50)
    print("       CICLO CONCLUÍDO")
    print("=" * 50)
    print("\nEstados analisados")
    print("Comandos processados")
    print("Carregadores atualizados")
    print("Automação finalizada")
    print("\nVisualize os resultados com: streamlit run dashboard.py")


if __name__ == "__main__":
    main()
