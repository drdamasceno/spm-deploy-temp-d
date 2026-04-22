-- 0001_seed_empresa_categoria.sql
-- Seeds para operação inicial: empresas SPM e FD + categorias derivadas
-- do arquivo real SPM-Orcamento-04.2026.xlsx

INSERT INTO empresa (codigo, razao_social, cnpj) VALUES
  ('SPM', 'SOCIEDADE PARANAENSE DE MEDICINA LTDA', '37.092.326/0001-04'),
  ('FD',  'FD GESTAO INTELIGENTE DE NEGOCIOS LTDA', '49.542.886/0001-94')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO categoria_despesa (nome) VALUES
  ('Diretoria Geral'),
  ('Comissões de Licitações e Credenciamentos'),
  ('Assessoria Juridica'),
  ('Salarios e Comissão de Escalistas'),
  ('Salários'),
  ('Salários ADM'),
  ('Salários ADM - Rescisão'),
  ('Setor Licitações e equipe de apoio'),
  ('Assessoria Juridica de Licitações e equipe de apoio'),
  ('Licitações - Diretoria de Licitação'),
  ('Diretoria Médica'),
  ('Coordenações Médicas Não Atribuidas Diretamente aos projetos'),
  ('Aluguel e Coworking, vistorias e Reformas Imovel locado'),
  ('Limpeza e serviços gerais'),
  ('Energia Elétrica'),
  ('Telefonia Internet'),
  ('Condomínio'),
  ('Software PegaPlantão, Omie, Digisac, Microsoft, Videogen, Chatgpt, Aplle'),
  ('Contabilidade'),
  ('Contabilidade FD'),
  ('Despesas Diretoria Geral'),
  ('Assistência Médica'),
  ('ISS'),
  ('DARF PREVIDENCIARIA INSS E ENCARGOS'),
  ('Retenção - PIS/COFINS/CSLL Prestadores de Serviços'),
  ('FGTS'),
  ('FGTS- GUIA DE RESCISÕES UNAI/MG'),
  ('COFINS FATURAMENTO'),
  ('PIS FATURAMENTO'),
  ('TRIMESTRE IRPJ'),
  ('TRIMESTRE CSLL'),
  ('Coordenação de Contratos/Coordenação Médica Apropriadas aos Projetos'),
  ('Serviços de Enfermagem/Despesas Gerais'),
  ('Publicidade Propaganda e Brindes'),
  ('ADIANTAMENTO DE SALÁRIOS ADM- FD'),
  ('Frete/Passagens/despesas viagem/Hospedagem Medicos dos projetos'),
  ('Despesas Gerais com Editais'),
  ('Água e Esgoto'),
  ('Despesas Viagens de UBER'),
  ('Provisão para Gastos Eventuais'),
  ('ROUPAS'),
  ('MEDICOS SM24'),
  ('ADMINISTRATIVOS SM24 - CLT'),
  ('Equipamentos'),
  ('Cartão de Crédito'),
  ('Serviços Mensal Estimados de Contratados Serviços Médicos'),
  ('PONTO ELETRONICO'),
  ('Parcelamento')
ON CONFLICT (nome) DO NOTHING;
