"""
ChargeGrid Intelligence - Regras de decisão (lógica pura, sem acesso ao banco).

Separar a lógica do acesso ao Supabase permite testar as regras,
reutilizá-las no dashboard e explicar o algoritmo (Pensamento Computacional).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")

# Faixas tarifárias (mesmos valores exibidos no aplicativo)
TARIFAS = {"Fora de pico": 0.65, "Normal": 0.85, "Pico": 1.20}

# Limites operacionais dos carregadores (kW)
PASSO_KW = 50
POTENCIA_MIN_KW = 50
POTENCIA_MAX_KW = 200

# Limites da bateria (%)
BATERIA_MIN = 20
BATERIA_CHEIA = 95

# Fator médio de emissão da rede (SIN) em kg CO2 por kWh.
# Referência: MCTI, média de 2023 = 38,5 kg CO2/MWh. Em 2025 os valores
# mensais ficaram entre 21,5 e 28,9 kg/MWh. Atualize se necessário.
FATOR_EMISSAO_KG_KWH = 0.0385


def hora_atual():
    return datetime.now(FUSO).hour


def faixa_tarifaria(hora):
    """Retorna 'Fora de pico' (22h-7h), 'Normal' (7h-18h) ou 'Pico' (18h-22h)."""
    if hora >= 22 or hora < 7:
        return "Fora de pico"
    if hora < 18:
        return "Normal"
    return "Pico"


def tarifa_da_hora(hora):
    return TARIFAS[faixa_tarifaria(hora)]


def acao_bateria(bateria, situacao, faixa):
    """Decide o que fazer com a bateria (armazenamento)."""
    # Prioridade: demanda elevada > excedente solar > horário de pico.
    # Com excedente solar a bateria carrega, mesmo no pico (a energia é gratuita).
    if situacao == "demanda_elevada":
        return "DESCARREGAR" if bateria > BATERIA_MIN else "MANTER"
    if situacao == "solar":
        return "CARREGAR" if bateria < BATERIA_CHEIA else "MANTER"
    if faixa == "Pico":
        return "DESCARREGAR" if bateria > BATERIA_MIN else "MANTER"
    return "MANTER"


def reais(valor):
    """Formata em reais com vírgula decimal, por exemplo R$ 1,20."""
    return "R$ " + f"{valor:.2f}".replace(".", ",")


def recomendacao_pico(faixa):
    """Em horário de pico, recomenda recarregar na faixa de menor tarifa."""
    if faixa != "Pico":
        return None
    economia = (1 - TARIFAS["Fora de pico"] / TARIFAS["Pico"]) * 100
    return (
        f"Horário de pico ({reais(TARIFAS['Pico'])}/kWh): recomendar recarga entre "
        f"22h e 7h ({reais(TARIFAS['Fora de pico'])}/kWh), economia de {economia:.0f}%."
    )


def decidir(estado, carregadores, hora):
    """
    Algoritmo central. Recebe o estado energético, os carregadores da estação
    e a hora, e devolve a decisão (sem gravar nada).

    Prioridade das regras:
      1. demanda > potência disponível  -> REDUZIR um carregador ocupado
      2. status 'Energia solar disponível' -> AUMENTAR (pré-ajuste de capacidade
         de um carregador livre, aproveitando o excedente solar)
      3. caso contrário -> MANTER
    Bateria e horário de pico complementam a decisão.
    """
    demanda = float(estado["demanda_kw"])
    disponivel = float(estado["potencia_disponivel_kw"])
    bateria = float(estado.get("bateria_percentual") or 0)
    faixa = faixa_tarifaria(hora)

    if demanda > disponivel:
        situacao = "demanda_elevada"
    elif estado.get("status_gerenciamento") == "Energia solar disponível":
        situacao = "solar"
    else:
        situacao = "normal"

    bat = acao_bateria(bateria, situacao, faixa)
    resultado = {
        "situacao": situacao,
        "faixa": faixa,
        "bateria_acao": bat,
        "recomendacao": recomendacao_pico(faixa),
        "comando": None,
        "mensagem": "Nenhum comando será criado.",
    }
    sufixo = f" | Bateria: {bat} ({bateria:.0f}%)"

    if situacao == "demanda_elevada":
        alvo = next((c for c in carregadores if c["status"].lower() == "ocupado"), None)
        if alvo is None:
            resultado["mensagem"] = "Demanda elevada, mas nenhum carregador ocupado."
            return resultado
        atual = float(alvo["potencia_kw"])
        nova = max(atual - PASSO_KW, POTENCIA_MIN_KW)
        if nova < atual:
            resultado["comando"] = {
                "tipo_comando": "REDUZIR",
                "carregador_id": alvo["id"],
                "potencia_anterior_kw": atual,
                "potencia_nova_kw": nova,
                "motivo": "Demanda elevada" + sufixo,
            }
        else:
            resultado["mensagem"] = f"Carregador {alvo['id']} já está no limite mínimo."

    elif situacao == "solar":
        alvo = next((c for c in carregadores if c["status"].lower() == "livre"), None)
        if alvo is None:
            resultado["mensagem"] = "Solar disponível, mas nenhum carregador livre."
            return resultado
        atual = float(alvo["potencia_kw"])
        nova = min(atual + PASSO_KW, POTENCIA_MAX_KW)
        if nova > atual:
            resultado["comando"] = {
                "tipo_comando": "AUMENTAR",
                "carregador_id": alvo["id"],
                "potencia_anterior_kw": atual,
                "potencia_nova_kw": nova,
                "motivo": "Energia solar disponível" + sufixo,
            }
        else:
            resultado["mensagem"] = f"Carregador {alvo['id']} já está no limite máximo."

    return resultado


def calcular_impacto(estados, tarifa_kwh=TARIFAS["Normal"], intervalo_h=1.0):
    """
    Impacto simulado. Cada registro de estado_energetico é tratado como uma
    medição que dura `intervalo_h` hora (premissa de simulação).
    """
    solar_usado = sum(
        min(float(e["energia_solar_kW"]), float(e["demanda_kw"])) for e in estados
    ) * intervalo_h
    excedente = sum(
        max(float(e["energia_solar_kW"]) - float(e["demanda_kw"]), 0) for e in estados
    ) * intervalo_h
    solar_total = sum(float(e["energia_solar_kW"]) for e in estados) * intervalo_h
    rede_total = sum(float(e["energia_rede_kw"]) for e in estados) * intervalo_h
    demanda_total = sum(float(e["demanda_kw"]) for e in estados) * intervalo_h

    return {
        "solar_total_kwh": solar_total,
        "rede_total_kwh": rede_total,
        "demanda_total_kwh": demanda_total,
        "solar_usado_kwh": solar_usado,
        "excedente_para_bateria_kwh": excedente,
        "economia_reais": solar_usado * tarifa_kwh,
        "co2_evitado_kg": solar_usado * FATOR_EMISSAO_KG_KWH,
        "autossuficiencia_pct": (solar_usado / demanda_total * 100) if demanda_total else 0.0,
    }
