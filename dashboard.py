"""
ChargeGrid Intelligence - Dashboard
Executar com:  streamlit run dashboard.py
"""

from decimal import ROUND_HALF_UP, Decimal

import pandas as pd
import streamlit as st
import banco
import regras

st.set_page_config(page_title="ChargeGrid Intelligence", layout="wide")


def brl(valor):
    """Formata em reais (R$ 1.234,56) arredondando 0,005 para cima."""
    d = Decimal(str(valor)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return "R$ " + f"{d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(valor, casas=1):
    """Formata número com vírgula decimal, por exemplo 13,5."""
    return f"{valor:.{casas}f}".replace(".", ",")


def carregar(tabela):
    return pd.DataFrame(banco.conectar().tabela(tabela))


st.title("ChargeGrid Intelligence")
st.caption(
    "Gestão inteligente de energia solar, bateria e recarga de veículos elétricos "
    f"| Fonte de dados: {banco.BACKEND}"
)

if st.button("Atualizar dados"):
    st.rerun()

estados = carregar("estado_energetico")
carregadores = carregar("carregadores")
comandos = carregar("comandos_de_automacao")
sessoes = carregar("sessoes_carregamento")

# ---------- Tarifa atual ----------
hora = regras.hora_atual()
faixa = regras.faixa_tarifaria(hora)
c1, c2, c3 = st.columns(3)
c1.metric("Hora (São Paulo)", f"{hora}h")
c2.metric("Faixa tarifária", faixa)
c3.metric("Tarifa atual", brl(regras.TARIFAS[faixa]) + "/kWh")

recomendacao = regras.recomendacao_pico(faixa)
if recomendacao:
    st.warning(recomendacao.replace("$", r"\$"))

if estados.empty:
    st.error("Nenhum registro em estado_energetico.")
    st.stop()

# ---------- Impacto ----------
st.subheader("Impacto de sustentabilidade (simulado)")
imp = regras.calcular_impacto(estados.to_dict("records"))
m1, m2, m3, m4 = st.columns(4)
m1.metric("Solar aproveitado", f"{num(imp['solar_usado_kwh'])} kWh")
m2.metric("Economia estimada", brl(imp["economia_reais"]))
m3.metric("CO₂ evitado", f"{num(imp['co2_evitado_kg'], 2)} kg")
m4.metric("Autossuficiência solar", f"{imp['autossuficiencia_pct']:.0f}%")
st.caption(
    f"Premissa: cada estado energético equivale a 1 hora de operação. "
    f"Fator de emissão da rede: {num(regras.FATOR_EMISSAO_KG_KWH * 1000)} kg CO₂/MWh (MCTI, SIN 2023). "
    f"Excedente solar enviado à bateria: {num(imp['excedente_para_bateria_kwh'])} kWh."
)

# ---------- Energia por estado ----------
st.subheader("Solar × Rede × Demanda")
grafico = pd.DataFrame(
    {
        "Solar (kW)": estados["energia_solar_kW"],
        "Rede (kW)": estados["energia_rede_kw"],
        "Demanda (kW)": estados["demanda_kw"],
        "Potência disponível (kW)": estados["potencia_disponivel_kw"],
    }
)
grafico.index = [f"Estado {i}" for i in estados["id"]]
st.bar_chart(grafico, stack=False, height=380)

# ---------- Bateria e decisão atual ----------
st.subheader("Bateria e decisão do sistema")
linhas = []
for _, estado in estados.iterrows():
    cars = carregadores[carregadores["id_estacao"] == estado["estacao_id"]].to_dict("records")
    d = regras.decidir(estado.to_dict(), cars, hora)
    cmd = d["comando"]
    linhas.append(
        {
            "Estado": estado["id"],
            "Estação": estado["estacao_id"],
            "Bateria (%)": estado["bateria_percentual"],
            "Ação da bateria": d["bateria_acao"],
            "Situação": d["situacao"],
            "Decisão": cmd["tipo_comando"] if cmd else "MANTER",
        }
    )
st.dataframe(pd.DataFrame(linhas), hide_index=True)
st.caption("A coluna Decisão mostra o que o sistema faria no próximo ciclo, com as potências atuais dos carregadores.")

# ---------- Carregadores ----------
st.subheader("Carregadores")
st.dataframe(carregadores, hide_index=True)

# ---------- Comandos ----------
st.subheader("Comandos de automação")
if comandos.empty:
    st.info("Nenhum comando registrado ainda. Rode main.py para gerar.")
else:
    cols = [
        "id", "tipo_comando", "carregador_id", "potencia_anterior_kw",
        "potencia_nova_kw", "motivo", "executado", "executado_em",
    ]
    st.dataframe(
        comandos[[c for c in cols if c in comandos.columns]],
        hide_index=True,
    )

# ---------- Sessões ----------
st.subheader("Sessões de carregamento")
if sessoes.empty:
    st.info("Nenhuma sessão registrada.")
else:
    s1, s2, s3 = st.columns(3)
    s1.metric("Sessões", len(sessoes))
    s2.metric("Energia total", f"{num(sessoes['energia_kWh'].fillna(0).sum())} kWh")
    s3.metric("Custo total", brl(sessoes["custo"].fillna(0).sum()))
