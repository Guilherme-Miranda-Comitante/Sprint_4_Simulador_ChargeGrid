"""Testes das regras de decisão. Executar: python test_regras.py"""
import regras

def estado(solar, rede, demanda, disp, bateria=50, status="Normal"):
    return {"energia_solar_kW": solar, "energia_rede_kw": rede, "demanda_kw": demanda,
            "potencia_disponivel_kw": disp, "bateria_percentual": bateria,
            "status_gerenciamento": status}

def test_faixas():
    assert regras.faixa_tarifaria(23) == "Fora de pico"
    assert regras.faixa_tarifaria(3) == "Fora de pico"
    assert regras.faixa_tarifaria(7) == "Normal"
    assert regras.faixa_tarifaria(17) == "Normal"
    assert regras.faixa_tarifaria(18) == "Pico"
    assert regras.faixa_tarifaria(21) == "Pico"

def test_normal_mantem():
    d = regras.decidir(estado(8.5, 0, 5.5, 10), [{"id": 1, "status": "Ocupado", "potencia_kw": 150}], 10)
    assert d["situacao"] == "normal" and d["comando"] is None

def test_demanda_elevada_reduz():
    cars = [{"id": 1, "status": "Livre", "potencia_kw": 150},
            {"id": 2, "status": "Ocupado", "potencia_kw": 150}]
    d = regras.decidir(estado(3, 9, 12, 5), cars, 10)
    c = d["comando"]
    assert c["tipo_comando"] == "REDUZIR" and c["carregador_id"] == 2
    assert (c["potencia_anterior_kw"], c["potencia_nova_kw"]) == (150, 100)

def test_solar_aumenta():
    cars = [{"id": 1, "status": "Livre", "potencia_kw": 150}]
    d = regras.decidir(estado(15, 0, 5, 15, 60, "Energia solar disponível"), cars, 12)
    c = d["comando"]
    assert c["tipo_comando"] == "AUMENTAR" and c["potencia_nova_kw"] == 200
    assert d["bateria_acao"] == "CARREGAR"

def test_limites():
    d = regras.decidir(estado(3, 9, 12, 5), [{"id": 2, "status": "Ocupado", "potencia_kw": 50}], 10)
    assert d["comando"] is None
    d = regras.decidir(estado(15, 0, 5, 15, 60, "Energia solar disponível"),
                       [{"id": 1, "status": "Livre", "potencia_kw": 200}], 12)
    assert d["comando"] is None

def test_pico_recomenda_e_descarrega_bateria():
    d = regras.decidir(estado(8, 0, 5, 10, 80), [], 19)
    assert d["recomendacao"] and d["bateria_acao"] == "DESCARREGAR"
    d = regras.decidir(estado(8, 0, 5, 10, 10), [], 19)
    assert d["bateria_acao"] == "MANTER"

def test_solar_no_pico_carrega_bateria():
    cars = [{"id": 1, "status": "Livre", "potencia_kw": 150}]
    d = regras.decidir(estado(15, 0, 5, 15, 60, "Energia solar disponível"), cars, 19)
    assert d["bateria_acao"] == "CARREGAR"      # excedente solar tem prioridade sobre o pico
    d = regras.decidir(estado(3, 9, 12, 5, 50), [], 19)
    assert d["bateria_acao"] == "DESCARREGAR"   # demanda elevada no pico

def test_impacto():
    r = regras.calcular_impacto([estado(15, 0, 5, 15), estado(3, 9, 12, 5)])
    assert r["solar_usado_kwh"] == 8          # min(15,5) + min(3,12)
    assert r["excedente_para_bateria_kwh"] == 10
    assert abs(r["co2_evitado_kg"] - 8 * regras.FATOR_EMISSAO_KG_KWH) < 1e-9

if __name__ == "__main__":
    for nome, fn in list(globals().items()):
        if nome.startswith("test_"):
            fn(); print("OK ", nome)
    print("\nTodos os testes passaram.")
