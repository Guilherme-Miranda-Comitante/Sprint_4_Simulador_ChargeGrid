-- =============================================================
-- ChargeGrid Intelligence - Dados de teste (100% simulados)
-- Execute DEPOIS de estrutura-banco.sql.
-- Cenários: normal, demanda elevada e solar disponível.
-- =============================================================

insert into estacoes (id, nome, endereco) values
    (1, 'EV Charge - Paulista',      'Av. Paulista, 1578'),
    (2, 'EV Charge - Pinheiros',     'R. dos Pinheiros, 840'),
    (3, 'EV Charge - Vila Olímpia',  'R. Funchal, 263');

insert into usuarios (id, nome) values (1, 'Guilherme Miranda');

insert into veiculos (id, usuario_id, modelo, placa, capacidade_kwh) values
    (1, 1, 'BYD Seal', 'ABC1D23', 75);

insert into tarifas (id, nome, preco_kwh) values
    (1, 'Fora de pico', 0.65),
    (2, 'Normal',       0.85),
    (3, 'Pico',         1.20);

insert into carregadores (id, id_estacao, status, potencia_kw) values
    (1, 1, 'Livre',   150),
    (2, 2, 'Ocupado', 150),
    (3, 3, 'Ocupado', 150),
    (4, 2, 'Livre',   150);

insert into estado_energetico
    (estacao_id, "energia_solar_kW", energia_rede_kw, demanda_kw, potencia_disponivel_kw,
     bateria_percentual, status_gerenciamento) values
    (3,  8.5, 0.0,  5.5, 10.0, 70, 'Normal'),
    (2,  3.0, 9.0, 12.0,  5.0, 50, 'Demanda elevada'),
    (1, 15.0, 0.0,  5.0, 15.0, 60, 'Energia solar disponível');

insert into sessoes_carregamento
    (estacao_id, carregador_id, usuario_id, veiculo_id, tarifa_id,
     tempo_inicial, tempo_final, "energia_kWh", custo, status) values
    (1, 1, 1, 1, 1, '2026-08-26 22:13:00-03', '2026-08-26 23:03:00-03', 2.2, 1.43, 'Concluída'),
    (2, 2, 1, 1, 3, '2026-08-17 21:14:00-03', '2026-08-17 21:34:00-03', 0.8, 0.96, 'Concluída');

-- Alinha as sequências dos ids após inserir valores explícitos
select setval(pg_get_serial_sequence('estacoes', 'id'),       (select max(id) from estacoes));
select setval(pg_get_serial_sequence('usuarios', 'id'),       (select max(id) from usuarios));
select setval(pg_get_serial_sequence('veiculos', 'id'),       (select max(id) from veiculos));
select setval(pg_get_serial_sequence('tarifas', 'id'),        (select max(id) from tarifas));
select setval(pg_get_serial_sequence('carregadores', 'id'),   (select max(id) from carregadores));
