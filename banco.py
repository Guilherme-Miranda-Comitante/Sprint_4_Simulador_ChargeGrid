"""
ChargeGrid Intelligence - Camada de acesso a dados.

Dois backends com a MESMA interface:
  - sqlite   : banco local (arquivo chargegrid.db). Não precisa de internet nem de credenciais.
  - supabase : PostgreSQL na nuvem. É o padrão quando SUPABASE_URL e SUPABASE_KEY existem.

Para forçar um deles, defina BACKEND=sqlite ou BACKEND=supabase no .env.
O restante do sistema (regras, automação, dashboard) não sabe qual backend está em uso.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TABELAS = (
    "estacoes",
    "carregadores",
    "estado_energetico",
    "comandos_de_automacao",
    "sessoes_carregamento",
    "tarifas",
    "usuarios",
    "veiculos",
)


def _escolher_backend():
    explicito = os.getenv("BACKEND", "").strip().lower()
    if explicito in ("sqlite", "supabase"):
        return explicito
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
        return "supabase"
    return "sqlite"


BACKEND = _escolher_backend()
CAMINHO_DB = Path(os.getenv("CHARGEGRID_DB", Path(__file__).with_name("chargegrid.db")))

# Esquema local. Mantém os mesmos nomes de tabelas e colunas do Supabase
# e declara chaves estrangeiras reais.
SCHEMA = """
CREATE TABLE IF NOT EXISTS estacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    endereco TEXT
);
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS veiculos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    modelo TEXT NOT NULL,
    placa TEXT,
    capacidade_kwh REAL
);
CREATE TABLE IF NOT EXISTS tarifas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    preco_kwh REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS carregadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_estacao INTEGER NOT NULL REFERENCES estacoes(id),
    status TEXT NOT NULL,
    potencia_kw REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS estado_energetico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    estacao_id INTEGER NOT NULL REFERENCES estacoes(id),
    energia_solar_kW REAL NOT NULL,
    energia_rede_kw REAL NOT NULL,
    demanda_kw REAL NOT NULL,
    potencia_disponivel_kw REAL NOT NULL,
    bateria_percentual REAL NOT NULL,
    status_gerenciamento TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS comandos_de_automacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    tipo_comando TEXT NOT NULL,
    potencia_anterior_kw REAL NOT NULL,
    carregador_id INTEGER NOT NULL REFERENCES carregadores(id),
    potencia_nova_kw REAL NOT NULL,
    motivo TEXT,
    executado INTEGER NOT NULL DEFAULT 0,
    executado_em TEXT
);
CREATE TABLE IF NOT EXISTS sessoes_carregamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    estacao_id INTEGER NOT NULL REFERENCES estacoes(id),
    carregador_id INTEGER NOT NULL REFERENCES carregadores(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    veiculo_id INTEGER NOT NULL REFERENCES veiculos(id),
    tarifa_id INTEGER NOT NULL REFERENCES tarifas(id),
    tempo_inicial TEXT,
    tempo_final TEXT,
    energia_kWh REAL,
    custo REAL,
    status TEXT
);
"""


def _agora():
    return datetime.now(timezone.utc).isoformat()


class _SQLite:
    nome = "sqlite"

    def __init__(self):
        # check_same_thread=False: o Streamlit executa o script em várias threads
        self.con = sqlite3.connect(CAMINHO_DB, check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.executescript(SCHEMA)

    def _linhas(self, sql, params=()):
        linhas = []
        for r in self.con.execute(sql, params).fetchall():
            d = dict(r)
            if "executado" in d:
                d["executado"] = bool(d["executado"])
            linhas.append(d)
        return linhas

    def tabela(self, nome):
        if nome not in TABELAS:
            raise ValueError(f"Tabela desconhecida: {nome}")
        return self._linhas(f"SELECT * FROM {nome} ORDER BY id")

    def estados(self):
        return self.tabela("estado_energetico")

    def carregadores(self, estacao_id):
        return self._linhas("SELECT * FROM carregadores WHERE id_estacao = ? ORDER BY id", (estacao_id,))

    def tem_comando_pendente(self, carregador_id):
        return bool(
            self._linhas(
                "SELECT id FROM comandos_de_automacao WHERE carregador_id = ? AND executado = 0 LIMIT 1",
                (carregador_id,),
            )
        )

    def criar_comando(self, c):
        cur = self.con.execute(
            "INSERT INTO comandos_de_automacao "
            "(tipo_comando, potencia_anterior_kw, carregador_id, potencia_nova_kw, motivo, executado) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            (c["tipo_comando"], c["potencia_anterior_kw"], c["carregador_id"],
             c["potencia_nova_kw"], c["motivo"]),
        )
        self.con.commit()
        return self._linhas("SELECT * FROM comandos_de_automacao WHERE id = ?", (cur.lastrowid,))

    def comandos_pendentes(self):
        return self._linhas("SELECT * FROM comandos_de_automacao WHERE executado = 0 ORDER BY id")

    def atualizar_potencia(self, carregador_id, nova_potencia):
        self.con.execute("UPDATE carregadores SET potencia_kw = ? WHERE id = ?", (nova_potencia, carregador_id))
        self.con.commit()

    def marcar_executado(self, comando_id):
        self.con.execute(
            "UPDATE comandos_de_automacao SET executado = 1, executado_em = ? WHERE id = ?",
            (_agora(), comando_id),
        )
        self.con.commit()


class _Supabase:
    nome = "supabase"

    def __init__(self):
        url, chave = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
        if not url or not chave:
            raise RuntimeError("Defina SUPABASE_URL e SUPABASE_KEY no .env, ou use BACKEND=sqlite.")
        from supabase import create_client  # import tardio: o modo sqlite não precisa do pacote

        self.sb = create_client(url, chave)

    def tabela(self, nome):
        if nome not in TABELAS:
            raise ValueError(f"Tabela desconhecida: {nome}")
        return self.sb.table(nome).select("*").order("id").execute().data

    def estados(self):
        return self.tabela("estado_energetico")

    def carregadores(self, estacao_id):
        return self.sb.table("carregadores").select("*").eq("id_estacao", estacao_id).execute().data

    def tem_comando_pendente(self, carregador_id):
        r = (
            self.sb.table("comandos_de_automacao").select("id")
            .eq("carregador_id", carregador_id).eq("executado", False).limit(1).execute()
        )
        return len(r.data) > 0

    def criar_comando(self, c):
        return self.sb.table("comandos_de_automacao").insert({**c, "executado": False}).execute().data

    def comandos_pendentes(self):
        return (
            self.sb.table("comandos_de_automacao").select("*")
            .eq("executado", False).order("id").execute().data
        )

    def atualizar_potencia(self, carregador_id, nova_potencia):
        self.sb.table("carregadores").update({"potencia_kw": nova_potencia}).eq("id", carregador_id).execute()

    def marcar_executado(self, comando_id):
        (
            self.sb.table("comandos_de_automacao")
            .update({"executado": True, "executado_em": _agora()})
            .eq("id", comando_id).execute()
        )


_instancia = None


def conectar():
    """Devolve o backend configurado (uma única instância por processo)."""
    global _instancia
    if _instancia is None:
        _instancia = _SQLite() if BACKEND == "sqlite" else _Supabase()
    return _instancia


def recriar_sqlite():
    """
    Recria as tabelas do banco local (usado pelo simulador).
    Não apaga o arquivo: assim outro processo que o esteja usando
    (por exemplo, o dashboard aberto) continua funcionando, inclusive no Windows.
    """
    db = conectar()
    db.con.execute("PRAGMA foreign_keys = OFF")
    for tabela in reversed(TABELAS):
        db.con.execute(f"DROP TABLE IF EXISTS {tabela}")
    db.con.commit()
    db.con.execute("PRAGMA foreign_keys = ON")
    db.con.executescript(SCHEMA)
    return db
