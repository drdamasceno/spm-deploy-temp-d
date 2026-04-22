-- seed.sql
-- Passo 2 do plano v1 — dados iniciais do SPM Sistema Financeiro
-- Universo transcrito: rodada do motor 19fa14b sobre PP consolidado 02/2026
--   (arquivo 'SPM - FB - Conf. 01 a 09.04.2026.Claudexlsx.xlsx')
-- Esperado: 246 prestadores, 115 contratos, 374 registro_pp
--   (213 ELEGIVEL + 148 SEM_MOVIMENTO + 13 SALDO_NEGATIVO)
-- Excecoes PJ: 3 (Fabio, Glenio, Nayara)
-- Dependencias: migration 0001 aplicada + 0002 aplicada
-- Divida tecnica explicita:
--   1. conta_bancaria Bradesco Remessas com agencia/conta placeholder — atualizar via UI
--   2. 60 prestadores com cpf_cnpj_validado=false (placeholder PENDENTE:PIX_<TIPO>:<CHAVE>)
--      — atualizar via UI quando o relatorio de dados pessoais completo do PP for carregado
--   3. senha temporaria auth.users SpmTroca2026! — Hugo troca apos primeiro login
--   4. contrato.tipo='PUBLICO' hardcoded — SPM tem mix publico/privado; atualizar via UI
--      quando cadastro de contratos tiver tela de edicao
--
-- Notas sobre compatibilidade com GoTrue (descobertas no smoke test do Bloco A, 2026-04-19):
--   - INSERT em auth.users define confirmation_token/recovery_token/email_change_token_new/email_change
--     como '' (string vazia). GoTrue faz scan dessas colunas como string NOT NULL no sign-in —
--     NULL quebra com "Database error querying schema" (500).
--   - INSERT em auth.identities abaixo e obrigatorio para sign_in_with_password funcionar.
--     Seed manual em auth.users (fora do fluxo de signup) nao cria identity automatica.
--   - Migration 0004 concede SELECT em public.usuario para o role supabase_auth_admin
--     (GoTrue consulta essa tabela durante o login para popular claims do JWT).

BEGIN;

-- =====================================================
-- 1. AUTH + USUARIO (Hugo CEO)
-- =====================================================
INSERT INTO auth.users (
  id, instance_id, email, encrypted_password, email_confirmed_at,
  created_at, updated_at, raw_app_meta_data, raw_user_meta_data,
  aud, role,
  confirmation_token, recovery_token, email_change_token_new, email_change
) VALUES (
  '09ac0652-a1f1-467c-b072-33dc1f740fd7'::uuid,
  '00000000-0000-0000-0000-000000000000'::uuid,
  'dr.damasceno@spmbr.com',
  crypt('SpmTroca2026!', gen_salt('bf')),
  now(), now(), now(),
  '{"provider":"email","providers":["email"]}'::jsonb,
  '{}'::jsonb,
  'authenticated', 'authenticated',
  '', '', '', ''   -- GoTrue espera string vazia; NULL quebra o scan no sign-in
);

-- Identity do provider 'email' — obrigatoria para sign_in_with_password (GoTrue moderno)
INSERT INTO auth.identities (
  user_id, provider_id, provider, identity_data, created_at, updated_at
) VALUES (
  '09ac0652-a1f1-467c-b072-33dc1f740fd7'::uuid,
  '09ac0652-a1f1-467c-b072-33dc1f740fd7',
  'email',
  jsonb_build_object(
    'sub', '09ac0652-a1f1-467c-b072-33dc1f740fd7',
    'email', 'dr.damasceno@spmbr.com',
    'email_verified', true,
    'phone_verified', false
  ),
  now(), now()
);

INSERT INTO usuario (id, nome, email, perfil, fa_habilitado)
VALUES ('09ac0652-a1f1-467c-b072-33dc1f740fd7'::uuid, 'Hugo Fernandes Damasceno', 'dr.damasceno@spmbr.com', 'CEO', false);

-- =====================================================
-- 2. CONTA_BANCARIA (placeholder — atualizar via UI)
-- =====================================================
INSERT INTO conta_bancaria (id, banco, agencia, conta, finalidade, ativo)
VALUES ('69d80fb1-b166-4c17-b666-ae60d50fab59'::uuid, '237', '0000', '0000000', 'REMESSAS', true);

-- =====================================================
-- 3. PRESTADORES (246)
-- =====================================================
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('86fe9648-3b7c-4b65-98aa-7c65a07b6189'::uuid, 'ADRIEL HUMBERTO DE OLIVEIRA', '000000000/MG', 'MG', false, 'CNPJ', '44.238.070/0001-58', true, 'ADRIEL HUMBERTO DE OLIVEIRA', '44.238.070/0001-58');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('f0dfc745-4322-4e3e-acbb-907809ff4eee'::uuid, 'ANA CAROLINA ALVES CORREA', '943482/MG', 'MG', false, 'CPF', '138.027.366-80', true, NULL, '138.027.366-80');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('5176f65e-b9d7-492a-a449-5457dddd8d94'::uuid, 'DR ADRIANO VOINICHS DE FREITAS', '245217/SP', 'SP', false, 'CNPJ', '51.153.697/0001-71', true, 'AVF SERVICOS MEDICOS LTDA', '51.153.697/0001-71');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('97fdb7fb-f017-47d2-8539-549d43cce144'::uuid, 'DR ALAIN SUARES MILANES', '108859/MG', 'MG', false, 'CNPJ', '60.353.955/0001-54', true, 'MILANES MED LTDA', '60.353.955/0001-54');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('60db1059-519f-420d-acf4-89526f4da899'::uuid, 'DR ALONSO FREIRE RETTORE MENDES', '53031/MG', 'MG', false, 'CPF', '045.224.289-44', true, NULL, '045.224.289-44');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('ad694ac4-8e54-4aca-86cb-75fb8f63b920'::uuid, 'DR ANDRE FERNANDO HALLAK RICCIO', '85849/SP', 'SP', false, 'CNPJ', '50.325.362/0001-20', true, 'Andre Fernando Hallak Riccio Ltda', '50.325.362/0001-20');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('0daee7dd-568c-40a3-b94a-b472d81a147f'::uuid, 'DR AUGUSTO PATRYCIO SOUSA CAVALCANTE', '17128/PB', 'PB', false, 'CPF', '014.847.493-40', true, NULL, '014.847.493-40');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('4803fdc2-7108-4d8c-b56e-9ca7f1819523'::uuid, 'DR AUGUSTO SEVERO MENDES MITTMANN', '57767/SC', 'SC', false, 'CNPJ', '57.751.673/0001-09', true, 'MENDES&MITTMANN MEDICAL SUPORT', '57.751.673/0001-09');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('ad8686e7-aee8-410c-b5bf-82b090b9c116'::uuid, 'DR BRENNO MADUREIRA PESSI', '61037/PR', 'PR', false, 'CNPJ', '61.432.432/0001-66', true, 'BRENNO PESSI SERVICOS MEDICOS LTDA', '61.432.432/0001-66');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('8a05e984-cee5-4afe-9333-36bd4de08c5e'::uuid, 'DR BRUNO TADASHI YAMAMOTO TANAKA', '240940/SP', 'SP', false, 'CNPJ', '49.445.550/0001-03', true, 'B. T. Y. TANAKA SERVIÇOS MÉDICOS LTDA', '49.445.550/0001-03');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('c2d0451c-cc7f-4469-8ea7-11d143f89fe6'::uuid, 'DR CAIO FERNANDO DE OLIVEIRA', '268144/SP', 'SP', false, 'CNPJ', '58.360.576/0001-40', true, 'CFOMED LTDA', '58.360.576/0001-40');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('c77431b4-256d-406a-98cc-2cda9610a6e0'::uuid, 'DR CAIQUE YOSHI YSHIZUKA NASCIMENTO', '259401/SP', 'SP', false, 'CNPJ', '55.632.641/0001-50', true, 'CAIQUE YOSHI ISHIZUKA NASCIMENTO LTDA', '55.632.641/0001-50');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('5602679b-b206-4633-b332-3d0bdebc639a'::uuid, 'DR CAMILO FRANCISCO RAMOS PEREZ', '49374/PR', 'PR', false, 'CPF', '067.549.571-74', true, NULL, '067.549.571-74');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('6d77e580-d79d-4b3b-b922-d093a884218c'::uuid, 'DR CEZAR AUGUSTO LAMBERTI', '60428/MG', 'MG', false, 'CNPJ', '35.348.604/0001-08', true, 'NEUROAR CLÍNICA MÉDICA LTDA', '35.348.604/0001-08');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d4fb45a9-ab07-4c74-b627-82897e7fa232'::uuid, 'DR CHARLES VITAL PEREIRA MASCARENHAS', '2407/RR', 'RR', false, 'CPF', '011.365.225-90', true, NULL, '011.365.225-90');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('df03ab18-173d-4268-86aa-a2e0452270cd'::uuid, 'DR CHRISTIAN ALMEIDA DE OLIVEIRA', '105688/MG', 'MG', false, 'CPF', '120.844.106-06', true, NULL, '120.844.106-06');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('9734de36-f2f7-4e78-8e7a-52e7284af9d0'::uuid, 'DR CLENIO FERNANDES RODRIGUES', '45411/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99978-5576', false, NULL, '(38) 99978-5576');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('69b104af-86b8-4b86-951b-7a7477ad8b2e'::uuid, 'DR DALBERT SAMUEL DUTRA', '99259/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_EMAIL:INSTITUTODUTRAMED@GMAIL.COM', false, NULL, 'INSTITUTODUTRAMED@GMAIL.COM');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('cb4cd9a3-4ea8-4c08-b905-ec481f49b0da'::uuid, 'DR DANIEL DE OLIVEIRA AGLIO', '38295/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_EMAIL:vidallevepalhano@gmail.com', false, NULL, 'vidallevepalhano@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('860143b0-5c0e-49a2-80bb-976a57c5c1c2'::uuid, 'DR DANIEL JUSTINI DORNELLAS', '57886/PR', 'PR', false, 'CPF', '105.606.309-21', true, NULL, '105.606.309-21');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('55d7dcb3-a0cd-473c-9523-0673952a884c'::uuid, 'DR DIOGO AUGUSTO DE ALMEIDA GARRET', '27309/CE', 'CE', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(18) 98103-5677', false, NULL, '(18) 98103-5677');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('56b3d8d4-6d4a-45f9-8c79-af55cc91e182'::uuid, 'DR DIOGO PEREIRA BORGES', '31297/SC', 'SC', false, 'CPF', '405.898.398-10', true, NULL, '405.898.398-10');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('ebec3edc-0f6e-4f58-acb5-7d3ecc305a13'::uuid, 'DR DOUGLAS CORREA REIS', '58372/MG', 'MG', false, 'CPF', '062.676.246-41', true, NULL, '062.676.246-41');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('2af2a1a9-e1e9-4a8d-9ff4-c956065a2436'::uuid, 'DR EDMILSON ROQUE GUEDES NUNES', '64686/SP', 'SP', false, 'CNPJ', '07.723.515/0001-69', true, 'Clínica médica Nunes Ltda', '07.723.515/0001-69');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a5d0fc84-d5c4-4ab7-a838-eba105f9b9f4'::uuid, 'DR ENRICO RODRIGUES FAJOLI', '114905/MG', 'MG', false, 'CNPJ', '54.790.956/0001-63', true, 'FAJOLI SERVICOS EDUCACIONAIS LTDA', '54.790.956/0001-63');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('62590f5b-d06d-400a-b5c5-21c6b1571b8a'::uuid, 'DR ERIC VENANTE DE MATOS', '232121/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(19) 99415-0525', false, NULL, '(19) 99415-0525');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('86f2c3ea-4c76-438d-b37c-a974dfc08f78'::uuid, 'DR FABIO DE SOUZA SANTOS', '79665/MG', 'MG', false, 'CPF', '092.880.726-67', true, NULL, '092.880.726-67');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('81f5dbd0-7e5e-4756-aeed-091db642e50c'::uuid, 'DR FELIPE DE ARAUJO OLIVEIRA', '283534/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_ALEATORIA:e2207796-1118-47d4-b19e-e5b18d2af818', false, NULL, 'e2207796-1118-47d4-b19e-e5b18d2af818');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a7074742-a413-4641-a1c3-29123b1430eb'::uuid, 'DR FELIPE DE MORAIS', '111618/MG', 'MG', false, 'CNPJ', '59.621.646/0001-39', true, 'MORAIS ROSA SERVICOS MEDICOS LTDA', '59.621.646/0001-39');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('f5916daf-5c9f-427f-9fe7-07c698834b8e'::uuid, 'DR FELIPE JOSÉ CORREIA DE OLIVEIRA', '268443/SP', 'SP', false, 'CNPJ', '59.714.588/0001-98', true, 'CORREIA & OLIVEIRA CLINICAS MEDICAS LTDA Observação: Alteração solicitada dia 04/04/2025', '59.714.588/0001-98');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('6918d3ff-77d0-4ce0-8e11-2612613b878d'::uuid, 'DR FELIPE JUNIO COSTA', '268084/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(64) 99241-4570', false, NULL, '(64) 99241-4570');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('61ea2948-7eaf-4048-9236-8fa29f011f4d'::uuid, 'DR FELIPE OCTAVIO CARDOSO MATSUURA', '83097/MG', 'MG', false, 'CNPJ', '05.357.601/0001-70', true, 'CLÍNICA MATSUURA LTDA', '05.357.601/0001-70');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('6f8b9301-0c30-4844-bb1f-77ccd84b40a6'::uuid, 'DR FELIPE TEODORO VIEIRA ALVES', '62071/PR', 'PR', false, 'CNPJ', '61.650.847/0001-06', true, 'FELIPE TEODORO MEDICINA & SAUDE LTDA', '61.650.847/0001-06');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a76fbf1f-edf7-43c6-826c-de43c9842244'::uuid, 'DR FLÁVIO VASCONCELOS TORRES', '91095/MG', 'MG', false, 'CNPJ', '45.116.930/0001-43', true, 'RCE SOLUCOES EM MEDICINA LTDA', '45.116.930/0001-43');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e52a40c5-a4ba-4a21-8ee8-349a8da29760'::uuid, 'DR GABRIEL LANZA GEBIN', '224530/SP', 'SP', false, 'CPF', '441.812.968-57', true, NULL, '441.812.968-57');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('1092589d-ea85-4532-9edf-51e943276ab4'::uuid, 'DR GABRIEL PONTES SADER', '253492/SP', 'SP', false, 'CNPJ', '01.894.577/0001-57', true, 'CLIMATUS-CLINICA MEDICA SANTA EDVIRGES S/S', '01.894.577/0001-57');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('c2cfbd14-cc3f-4825-9053-ea17cbf2e1bf'::uuid, 'DR GABRIEL RODRIGO RODRIGUES PEREIRA', '34045/DF', 'DF', false, 'CPF', 'PENDENTE:PIX_EMAIL:drgabrielrodrigo@gmail.com', false, NULL, 'drgabrielrodrigo@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('908b6fc7-f007-4258-a240-15482c89b8fa'::uuid, 'DR GABRIEL SOARES DE AZEVEDO NETO', '273149/SP', 'SP', false, 'CNPJ', '61.070.283/0001-32', true, 'GABRIEL SOARES DE AZEVEDO NETO SERVICOS MEDICOS LTDA', '61.070.283/0001-32');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('5158f26f-4e3f-445e-8979-902d4369bb11'::uuid, 'DR GLENIO NEIVA JORDÃO', '57917/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99962-6364', false, NULL, '(38) 99962-6364');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('8dbd6ff7-6750-40a1-a34b-faa34f40840a'::uuid, 'DR GUSTAVO ARAUJO PINHEIRO', '215608/SP', 'SP', false, 'CPF', '981.214.481-15', true, NULL, '981.214.481-15');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a15cf41a-8d97-41f5-bf6c-df4ce9810883'::uuid, 'DR GUSTAVO RUGGERI RÉ Y GOYA', '268178/SP', 'SP', false, 'CNPJ', '58.523.271/0001-01', true, 'GUSTAVO RUGGERI RE Y GOYA LTDA', '58.523.271/0001-01');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('80ca9bcb-5033-4714-af71-1ceebdcc40b7'::uuid, 'DR HENRIQUE CAIXETA ROCHA', '112818/MG', 'MG', false, 'CPF', '133.610.296-94', true, NULL, '133.610.296-94');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('0bb6882c-a583-4ffa-aeca-b21ae07324b1'::uuid, 'DR HENRIQUE LICO DE SOUZA', '269230/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_EMAIL:md.henriquelico@gmail.com', false, NULL, 'md.henriquelico@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('21686ce4-48d0-4d34-b7be-c8c20c1c79f9'::uuid, 'DR HENRIQUE STORINO NETO', '116370/SP', 'SP', false, 'CNPJ', '33.622.951/0001-51', true, 'Henrique Storino Cirurgia Vascular Ltda', '33.622.951/0001-51');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('7785bbbd-92f6-4653-8ec5-4c6f45b63dd4'::uuid, 'DR IAN VARGAS MATEUS', '61723/PR', 'PR', false, 'CNPJ', '62.902.252/0001-63', true, 'IAN V. MATEUS SERVICOS MEDICOS', '62.902.252/0001-63');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('be5bd423-0ef2-4414-b1fa-6356369e0a32'::uuid, 'DR IBRAHIM NABIL ABDEL FATTAH IBRAHIM', '248492/SP', 'SP', false, 'CNPJ', '53.049.057/0001-41', true, 'IBRAHIM NABIL SERVICOS MEDICOS LTDA', '53.049.057/0001-41');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3140bc17-6d5c-4c03-b284-abee86d89823'::uuid, 'DR IVAN VILLANOVA E AFFONSO', '150210/SP', 'SP', false, 'CPF', '356.125.748-86', true, NULL, '356.125.748-86');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('dbb3a9d9-90e1-4daf-8752-42025dc45c59'::uuid, 'DR JEAN CARLO CARVALHO OLIVEIRA', '95055/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_EMAIL:drjccarvalho@gmail.com', false, NULL, 'drjccarvalho@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('7442b8e9-c426-4f19-aa08-b63638a56425'::uuid, 'DR JEFFERSON RODRIGUES DA SILVA', '77834/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_EMAIL:jeffersonrodrig@gmail.com', false, NULL, 'jeffersonrodrig@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('42847a10-edde-42c8-a44f-1f525f114131'::uuid, 'DR JOÃO HERMÍNIO DE OLIVEIRA', '268976/SP', 'SP', false, 'CNPJ', '32.419.924/0001-13', true, 'JOÃO HERMÍNIO DE OLIVEIRA', '32.419.924/0001-13');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('35e94720-a485-444c-9af8-af9a089dc662'::uuid, 'DR JOAQUIM TOMAZ DA SILVA', '30481/MG', 'MG', false, 'CPF', '519.421.356-53', true, NULL, '519.421.356-53');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('b1fa0861-7584-4a3a-ad45-d4afc8de9bf7'::uuid, 'DR JOSE ALBERTO IASBECH', '62833/SP', 'SP', false, 'CPF', '068.500.668-97', true, NULL, '068.500.668-97');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('ccd43d4b-c972-4a54-bdf5-8e22133cc519'::uuid, 'DR JUAN CARLOS COLQUE APAZA', '1928/RR', 'RR', false, 'CNPJ', '60.550.501/0001-73', true, 'APAZA SANOFARMA LTDA', '60.550.501/0001-73');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('ce8a6789-d809-4476-ab5e-1f2911b56c7d'::uuid, 'DR JULIANO SOUZA RAMOS MIOTO', '57351/PR', 'PR', false, 'CPF', 'PENDENTE:PIX_EMAIL:Julianomioto@gmail.com', false, NULL, 'Julianomioto@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('515f9fed-7971-4ef3-bde0-aef6737f0b2e'::uuid, 'DR JURACI MOREIRA', '22393/MG', 'MG', false, 'CNPJ', '42.359.853/0001-64', true, 'J M CLINICA MEDICA LTDA', '42.359.853/0001-64');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('28d526da-91df-471f-927a-812938ff7cfe'::uuid, 'DR LEANDRO CAIO CAPUCHINHO ROCHA', '64302/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99111-9066', false, NULL, '(38) 99111-9066');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('58c4a339-b09b-48d2-a588-5a11f0951cb8'::uuid, 'DR LEONARDO BERGARA DEVECHIO', '207212/SP', 'SP', false, 'CPF', '392.971.938-03', true, NULL, '392.971.938-03');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d5a80208-a9dc-4c7e-83b4-9a97728035cf'::uuid, 'DR LEONARDO DO COUTO ARAUJO', '36118/MG', 'MG', false, 'CNPJ', '22.090.692/0001-49', true, 'NEUROCENTER UNAI LTDA', '22.090.692/0001-49');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('9eaafac1-a807-49cd-bcfe-c40281410c5e'::uuid, 'DR LEONARDO SANTOS CARDOSO', '77704/MG', 'MG', false, 'CNPJ', '63.089.588/0001-11', true, 'LEONARDO SANTOS CARDOSO SERVICO MEDICOS LTDA', '63.089.588/0001-11');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('36f32488-2f23-4c9a-9b84-463ea9bc2957'::uuid, 'DR LOAMIR DA SILVA VIANA', '13850/AM', 'AM', false, 'CPF', '923.748.672-34', true, NULL, '923.748.672-34');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3dc744d3-40a4-4fab-841e-505cd1869f6c'::uuid, 'DR LUCAS DUARTE', '1787/RR', 'RR', false, 'CNPJ', '40.524.484/0001-92', true, 'PROCIRURGIC ATIVIDADE MEDICA LTDA', '40.524.484/0001-92');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d67b4437-7850-4297-b78b-38b0e89ae8c8'::uuid, 'DR LUCAS KASSIN GATTO SAMMOUR', '274976/SP', 'SP', false, 'CNPJ', '61.655.377/0001-73', true, 'Vital Medicina Lea Ltda', '61.655.377/0001-73');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e059f8f7-977d-4d53-9207-ed3ff42a3d8d'::uuid, 'DR LUCAS ODON ALENCAR AGUIAR', '278998/SP', 'SP', false, 'CNPJ', '64.090.125/0001-32', true, 'LUCAS ODON ALENCAR AGUIAR LTDA', '64.090.125/0001-32');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('579304fe-152a-47b0-9820-e7a15a48fe29'::uuid, 'DR LUCAS RYUITI ADATI', '251268/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(14) 99601-3584', false, NULL, '(14) 99601-3584');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('19e8785e-3afe-43cc-ac58-e642040995cf'::uuid, 'DR MANOEL JOÃO DA SILVA JUNIOR', '240965/SP', 'SP', false, 'CPF', '029.965.551-20', true, NULL, '029.965.551-20');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('8a1f5b67-9750-4472-b35f-eb89d375a326'::uuid, 'DR MARCELO DE CARVALHO RAMOS', '23616/SP', 'SP', false, 'CPF', '278.956.107-91', true, NULL, '278.956.107-91');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('74770cd5-37b9-4763-817c-aea383761fa4'::uuid, 'DR MARCELO LUIZ RUBIO', '214483/SP', 'SP', false, 'CNPJ', '37.970.536/0001-40', true, 'M. L. RUBIO CLINICA MEDICA LTDA', '37.970.536/0001-40');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('80b44046-1689-481e-8e2b-79ef3e123d35'::uuid, 'DR MARCELO MARQUES DA CUNHA', '1918/RR', 'RR', false, 'CPF', '807.241.912-91', true, NULL, '807.241.912-91');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('cefa8d1f-0e1f-4a7a-a809-b6cd1ff3c79b'::uuid, 'DR MARCELO MARQUES DA SILVA', '160411/SP', 'SP', false, 'CNPJ', '51.232.034/0001-42', true, 'MMS ASSISTENCIA A SAUDE LTDA', '51.232.034/0001-42');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('eec8122e-e221-4f82-95a5-54084615c792'::uuid, 'DR MARCELO UETI DE CAMARGO', '166020/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_EMAIL:odontologiauetimed@outlook.com', false, NULL, 'odontologiauetimed@outlook.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('359db675-fb60-4259-9557-c9c6883e2b9a'::uuid, 'DR MÁRCIO MARTINS RAFAEL', '12042/MG', 'MG', false, 'CNPJ', '73.494.825/0001-83', true, 'CLINOR LTDA', '73.494.825/0001-83');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('02085979-1013-4011-ade9-edf69e2b3ea6'::uuid, 'DR MÁRCIO MAZZONI FERREIRA DE CARVALHO', '27597/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99961-7048', false, NULL, '(38) 99961-7048');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('818f017c-19b6-4111-be90-ae9d87dcde5f'::uuid, 'DR MARCO ARON SOUZA HIERA', '60302/PR', 'PR', false, 'CNPJ', '58.320.309/0001-49', true, 'BONFIM HIERA SERVICOS MEDICOS LTDA', '58.320.309/0001-49');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('1835b261-a51d-43cf-84ee-5b299858cfc9'::uuid, 'DR MATEUS CAMILLO MIRANDA', '268589/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_EMAIL:mateus.camillo.miranda@hotmail.com', false, NULL, 'mateus.camillo.miranda@hotmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('db9098b8-5c70-4627-a5b6-1f6cc9297d82'::uuid, 'DR MATEUS SILVA LIMA', '3886212122/GO', 'GO', false, 'CNPJ', '64.201.691/0001-74', true, 'CRUZEIRO MEDCAR LTDA Observação: 64.201.691/0001-74', '64.201.691/0001-74');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('1d9e86c4-3b6f-4be4-a80d-c54d6a4d1030'::uuid, 'DR MATHEUS ALVES JORDÃO', '108596/MG', 'MG', false, 'CNPJ', '58.541.826/0001-48', true, 'JORDAN MEDICAL LTDA Observação: 58.541.826/0001-48', '58.541.826/0001-48');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('555efb7d-394c-4887-9d7d-891618586cba'::uuid, 'DR MATHEUS DE OLIVEIRA FURTADO', '275332/SP', 'SP', false, 'CPF', '149.984.866-83', true, NULL, '149.984.866-83');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('f8580fc7-0d4a-4f9b-871e-ae156a97012d'::uuid, 'DR MAXIMILIANO JOSÉ DE QUEIROZ', '62892/PR', 'PR', false, 'CNPJ', '64.156.175/0001-75', true, 'MAXIMILIANO JOSE DE QUEIROZ SERVICOS MEDICOS LTDA', '64.156.175/0001-75');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('96218abb-c520-42ab-bd0f-b15f0430b379'::uuid, 'DR MILTON CÉSAR JUKOVSKI', '89963/SP', 'SP', false, 'CNPJ', '25.065.328/0001-17', true, 'KMRC SERVIÇOS MÉDICOS SS', '25.065.328/0001-17');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a06e401e-d767-48a1-82d6-e722b56d1dc0'::uuid, 'DR MURILO CAXITO BITENCOURT', '93927/MG', 'MG', false, 'CNPJ', '48.982.204/0001-00', true, 'MEDICINA MURILO CAXITO BITENCOURT LTDA', '48.982.204/0001-00');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('998f28a7-e0b1-486a-8056-dab5b052f0d6'::uuid, 'DR OLIVER DE SOUZA ROSA', '61431/MG', 'MG', false, 'CNPJ', '47.622.701/0001-26', true, 'SROSA SAUDE LTDA', '47.622.701/0001-26');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('9dd08f9d-d14b-4233-846e-2e15770e49fe'::uuid, 'DR PAULO RICARDO OLIVEIRA DE LIMA', '47064/RS', 'RS', false, 'CPF', '360.380.162-87', true, NULL, '360.380.162-87');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('37dd7f1f-0c3f-48ff-aa28-46b5e34778ce'::uuid, 'DR PAULO ROBERTO SADY', '30984/MG', 'MG', false, 'CNPJ', '03.803.099/0001-58', true, 'CENTRO CLINICO NEURO-ORTOPEDICO DE UNAI LTDA', '03.803.099/0001-58');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d35cf18e-eb45-43b9-97eb-be89e7b4a6ce'::uuid, 'DR PAULO SÉRGIO MENDES NAHAS', '48158/SP', 'SP', false, 'CPF', '047.682.658-63', true, NULL, '047.682.658-63');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('ecd4b7d7-2939-4cd6-b12d-ea5bf2912315'::uuid, 'DR PEDRO DI GIOVANNI', '1615/RR', 'RR', false, 'CPF', '853.298.002-34', true, NULL, '853.298.002-34');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3d747e9a-16a7-4d52-ad35-396f597e9010'::uuid, 'DR PEDRO HENRIQUE DE OLIVEIRA DELLAROSA', '278547/SP', 'SP', false, 'CPF', '711.376.961-68', true, NULL, '711.376.961-68');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('46d6114c-99c7-4ebe-b390-87a2c19ba6ca'::uuid, 'DR PEDRO HENRIQUE LOPES DE OLIVEIRA', '33571/DF', 'DF', false, 'CNPJ', '56.058.832/0001-13', true, 'P & A ORTOPEDIA E REUMATOLOGIA LTDA', '56.058.832/0001-13');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('b0a31421-de11-4d01-8adb-7e4ce6525d04'::uuid, 'DR PEDRO HENRIQUE MANCINI VASSOURA', '260988/SP', 'SP', false, 'CNPJ', '57.273.338/0001-34', true, 'PEDRO H. MANCINI SAUDE LTDA', '57.273.338/0001-34');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('63d1c2f3-387a-46e0-a9fe-2e40bfdd8ff4'::uuid, 'DR PEDRO JOSE RICHARD', '53118/PR', 'PR', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(45) 99135-4085', false, NULL, '(45) 99135-4085');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('8b69e5b5-0e4f-46e6-b84b-9f6ebdd366fb'::uuid, 'DR PEDRO SOARES ORNELAS', '113268/MG', 'MG', false, 'CNPJ', '63.879.953/0001-91', true, 'PEDRO ORNELAS SERVICOS MEDICOS LTDA Observação: 63.879.953/0001-91', '63.879.953/0001-91');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a37f29db-58ac-4add-b595-d6296534c9de'::uuid, 'DR RAFAEL MAFRA DA SILVA', '57652/PR', 'PR', false, 'CPF', '056.232.741-02', true, NULL, '056.232.741-02');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('8a756442-c97c-47e9-92bb-6ab5e3d128a5'::uuid, 'DR RAFAEL PEREIRA DAVID MAIA', '242731/SP', 'SP', false, 'CNPJ', '33.105.718/0001-00', true, 'RAFAEL PEREIRA DAVID MAIA Observação: 33.105.718/0001-00', '33.105.718/0001-00');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('4848b036-add0-4b45-a486-544d3e1eb1ec'::uuid, 'DR RAMON LUCAS ROMUALDO', '62714/MG', 'MG', false, 'CPF', '086.533.426-99', true, NULL, '086.533.426-99');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('c081d69e-8a3e-4e2a-836b-eb404a203d8b'::uuid, 'DR RENAN COELHO WACHSMUTH', '112955/MG', 'MG', false, 'CNPJ', '63.914.633/0001-25', true, 'RENANCW SERVICOS MEDICOS LTDA Observação: 63.914.633/0001-25', '63.914.633/0001-25');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('5ba8156a-b115-48ce-b813-9130e4524ade'::uuid, 'DR RODRIGO ANDRADE DE SOUSA', '52574/MG', 'MG', false, 'CNPJ', '30.908.808/0001-32', true, 'RODRIGO ANDRADE DE SOUSA ME Observação: Nome Fantasia: CLÍNICA RAS', '30.908.808/0001-32');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('02061ff0-4ccd-4486-bd25-05f87f83e0aa'::uuid, 'DR RODRIGO ESTEVES ANDREU', '47258/MG', 'MG', false, 'CNPJ', '09.472.514/0001-14', true, 'RODRIGO ESTEVES ANDREU', '09.472.514/0001-14');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a6d012c5-f24a-479c-8244-d7e0bbaf537b'::uuid, 'DR RODRIGO MOREIRA GARCIA', '1207261/RJ', 'RJ', false, 'CPF', 'PENDENTE:PIX_ALEATORIA:c688114b-1e4f-436e-b857-d99756e9e04a', false, NULL, 'c688114b-1e4f-436e-b857-d99756e9e04a');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3f1583a7-c3b5-425b-9b5a-f9a40c59354a'::uuid, 'DR RODRIGO PRUDÊNCIO TEDESCHI', '268271/SP', 'SP', false, 'CNPJ', '58.639.643/0001-60', true, 'RODRIGO TEDESCHI SERVICOS MEDICOS LTDA', '58.639.643/0001-60');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('b829dd71-69ca-4a59-b67f-7d522ae79f0a'::uuid, 'DR RODRIGO QUEIROZ GUIMARAES', '142313/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_AUSENTE:', false, NULL, NULL);
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d9378788-3a6a-4bba-aa65-540095843ddf'::uuid, 'DR ROGER TAVARES PIRES', '182899/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(45) 99911-0226', false, NULL, '(45) 99911-0226');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d2da699f-18c6-4921-907a-79dde680bf8a'::uuid, 'DR ROMULO BONATO BONINI', '281762/SP', 'SP', false, 'CNPJ', '64.159.670/0001-38', true, 'ROMULO BONATO SERVICOS MEDICOS', '64.159.670/0001-38');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('f1ae332b-2e39-4e1e-935a-47fe4535e362'::uuid, 'DR RONY ROCHA DE OLIVEIRA JUNIOR', '94017/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_EMAIL:ronyjrmed@gmail.com', false, NULL, 'ronyjrmed@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('671af4d5-d664-40af-a513-031508aedc02'::uuid, 'DR ROSALVO RODRIGUES DOS SANTOS', '54893/MG', 'MG', false, 'CPF', '049.335.256-25', true, NULL, '049.335.256-25');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('140b6a22-309f-4fd6-8559-3410bc671110'::uuid, 'DR SAMUEL CALDEIRA MOTA', '98859/MG', 'MG', false, 'CPF', '124.849.916-65', true, NULL, '124.849.916-65');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('b78341b5-2143-435e-be61-89342a877eab'::uuid, 'DR SERGIO ANTONIO SANTARELLI', '44886/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_ALEATORIA:0452de58-dd71-4011-9d80-94e0a6d42dc6', false, NULL, '0452de58-dd71-4011-9d80-94e0a6d42dc6');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('cc0c3a6a-fd26-4153-8ccc-9305a5b32f2c'::uuid, 'DR TAINAN FABBRI SCALCO', '61221/PR', 'PR', false, 'CNPJ', '61.188.194/0001-95', true, 'TAINAN FABBRI SCALCO LTDA', '61.188.194/0001-95');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('bcef18bb-846c-4f74-a7a1-a70ebfd2d70f'::uuid, 'DR TIAGO CAETANO RODRIGUES', '89680/MG', 'MG', false, 'CPF', '084.620.906-36', true, NULL, '084.620.906-36');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3810c382-7859-4af3-af3e-14552abf653d'::uuid, 'DR TONY DYONE RIOS VIEGAS', '2406/RR', 'RR', false, 'CPF', '604.870.743-60', true, NULL, '604.870.743-60');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('f7218a0a-9abe-4c36-8ad0-4c9cb09a0d26'::uuid, 'DR VICTOR HUGO ALVES CAMPOS', '80834/MG', 'MG', false, 'CNPJ', '34.104.123/0001-94', true, 'CLINICA JV LTDA', '34.104.123/0001-94');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e78a5973-1978-4986-8a72-b6ff36c1e9c4'::uuid, 'DR VINICIUS MAGALHÃES UETI DE CAMARGO', '268370/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(18) 99630-6793', false, NULL, '(18) 99630-6793');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3ae43f80-bd75-4f9c-b31c-005f53cddc21'::uuid, 'DR VITOR AVILA DE OLIVEIRA', '99260/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(32) 99951-3136', false, NULL, '(32) 99951-3136');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d8b744f9-eb0a-468a-a1dc-3d6c188bdf84'::uuid, 'DR VITOR HUGO SOARES ROSA', '38751/GO', 'GO', false, 'CNPJ', '64.248.384/0001-49', true, 'VITOR HUGO SOARES ROSA LTDA Observação: 64.248.384/0001-49', '64.248.384/0001-49');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('18a9a79c-a2cb-48be-a167-78b520188f80'::uuid, 'DR VOSMAR PEREIRA CARDOSO', '64172/MG', 'MG', false, 'CPF', '791.354.126-15', true, NULL, '791.354.126-15');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('00925fd3-adc4-4fc4-9899-1579e2641308'::uuid, 'DR WILLIAM ANDREY CANDIDO DE LIMA', '238685/SP', 'SP', false, 'CPF', '094.569.839-94', true, NULL, '094.569.839-94');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d3eed807-516b-4c4e-9550-02325dce6c61'::uuid, 'DR YAGO JOSE SILVA VALETA', '274508/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_EMAIL:dryuribenicio@hotmail.com', false, NULL, 'dryuribenicio@hotmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('1405df85-540a-483c-ba4b-bfeb1cf6f745'::uuid, 'DRA ALANA SILVA FINOTTI', '247053/SP', 'SP', false, 'CNPJ', '51.514.268/0001-82', true, 'FINOTTI SERVICOS MEDICOS LTDA', '51.514.268/0001-82');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a6d0213e-d247-46ea-86b8-075e7d4ecf9f'::uuid, 'DRA ALESSANDRA CATTANEO', '62063/PR', 'PR', false, 'CNPJ', '62.757.633/0001-04', true, 'CATTANEO SERVICOS MEDICOS LTDA', '62.757.633/0001-04');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('69301a57-b3d1-48dd-894d-2384fbeaebc8'::uuid, 'DRA AMANDA FERRERA DE OLIVEIRA', '111353/MG', 'MG', false, 'CPF', '120.129.706-05', true, NULL, '120.129.706-05');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3f6f3ae4-7e6d-4b9f-909b-74798402fe72'::uuid, 'DRA AMY ANDRADE AMARAL', '247059/SP', 'SP', false, 'CNPJ', '51.511.209/0001-50', true, 'ANDRADE AMARAL SERVICOS MEDICOS LTDA', '51.511.209/0001-50');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('1ba889e7-c336-4361-ac9a-08c592e22497'::uuid, 'DRA ANA CARLA BORGES LACERDA', '105636/MG', 'MG', false, 'CNPJ', '58.092.853/0001-80', true, 'ACB LACERDA CLINICA MEDICA LTDA', '58.092.853/0001-80');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('91d36b05-8b3c-4f28-9db5-5fce13a33c64'::uuid, 'DRA ANA CAROLINA MURTA E SOUSA', '96570/MG', 'MG', false, 'CNPJ', '50.972.695/0001-41', true, 'M&S MEDICINA E SAUDE LTDA', '50.972.695/0001-41');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('ab5d4627-75d2-48b3-a2de-357666a86d28'::uuid, 'DRA ANA PAULA MARQUES ALVES', '29183/DF', 'DF', false, 'CNPJ', '37.230.796/0001-89', true, 'A&M SERVICOS MEDICOS LTDA', '37.230.796/0001-89');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('24e00bfd-f9fa-4bc7-b4c9-78d3b69a8da2'::uuid, 'DRA ANA VICTORIA CARVALHO PAIVA', '99213/MG', 'MG', false, 'CNPJ', '55.944.427/0001-30', true, 'ANA VICTORIA CARVALHO PAIVA LTDA', '55.944.427/0001-30');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('837e7228-1808-4b91-98af-20b64a075897'::uuid, 'DRA ANAÍS CARDOSO OLIVEIRA', '273704/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_EMAIL:anais_cardoso@hotmail.com', false, NULL, 'anais_cardoso@hotmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('bec16e98-43d7-4453-b4fe-ac01a39d04e8'::uuid, 'DRA ANDREA CAROLINA SIVILA CRUZ', '259070/SP', 'SP', false, 'CNPJ', '24.423.930/0001-16', true, 'LAGUNA CONSULTAS MEDICAS LTDA - ME', '24.423.930/0001-16');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('44e636d9-c75b-419b-9eb6-7b43c7779ea0'::uuid, 'DRA ANDRÉIA MORENO SILVA', '259874/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_EMAIL:andreiamoreno.s@hotmail.com', false, NULL, 'andreiamoreno.s@hotmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a787b2b9-21d5-4e37-8686-e4fe97c2671e'::uuid, 'DRA ANDRESSA TAVARES REZENDE', '271636/SP', 'SP', false, 'CNPJ', '60.541.934/0001-62', true, 'ATR ASSESSORIA E CONSULTORIA MEDICAS LTDA', '60.541.934/0001-62');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('fe861299-f85d-41ad-a5e4-caf99290b32f'::uuid, 'DRA ANGÉLICA GARCIA BORGI LINO DE SOUSA', '268124/SP', 'SP', false, 'CNPJ', '59.130.777/0001-13', true, 'NSF SERVICOS MEDICOS RIBEIRAO PRETO LTDA', '59.130.777/0001-13');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('ff912966-093b-4bc7-8b58-17f6aae83870'::uuid, 'DRA ANNA BEATRIZ LOURENÇO TIBERIO LIMA', '35064/DF', 'DF', false, 'CNPJ', '64.202.031/0001-08', true, 'ANNA BEATRIZ TIBERIO SERVICOS MEDICOS LTDA Observação: 64.202.031/0001-08', '64.202.031/0001-08');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('dece4ee4-5e40-4a50-8a08-f77154b91122'::uuid, 'DRA BARBARA ATAIDE CALDEIRA', '81579/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_EMAIL:barbara_ataide@hotmail.com', false, NULL, 'barbara_ataide@hotmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('cb914365-32f0-461c-a274-52889e6c1bca'::uuid, 'DRA BÁRBARA DE ALMEIDA MARTINSS', '265217/SP', 'SP', false, 'CNPJ', '58.636.278/0001-30', true, 'BARBARA MARTINS SERVICOS MEDICOS LTDA', '58.636.278/0001-30');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('4934ce04-2651-4fdb-a15f-b613d0b17e93'::uuid, 'DRA BEATRIZ LIMA DA FONSECA', '113273/MG', 'MG', false, 'CNPJ', '64.551.277/0001-95', true, 'Beatriz Lima da Fonseca Sevicos Médicos LTDA Observação: 64551277000195', '64.551.277/0001-95');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('cd5acf88-f67b-4e93-965a-b72e0f2d3395'::uuid, 'DRA BRENDA DE SA BATISTA', '106408/MG', 'MG', false, 'CNPJ', '58.772.572/0001-79', true, 'BRENDA DE SA BATISTA SERVICOS MEDICOS LTDA', '58.772.572/0001-79');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('89216d62-2478-4a43-acb8-e6f956275827'::uuid, 'DRA BRUNA KELLY CARDOSO DE CARVALHO', '55629/MG', 'MG', false, 'CNPJ', '29.690.128/0001-06', true, 'CARDOSO & CARVALHO SERVICOS MEDICOS LTDA Observação: 29.690.128/0001-06', '29.690.128/0001-06');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('61ba679a-7db1-4fbf-8f40-c708be2aeac0'::uuid, 'DRA CAMILA GARCEZ DE FREITAS MARTINS BORGES', '222296/SP', 'SP', false, 'CNPJ', '07.920.429/0001-46', true, 'CLINICA MEDICA MARTINS BORGES LTDA', '07.920.429/0001-46');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('ae5db091-1a6d-4843-be81-5a32dc2afa11'::uuid, 'DRA CAMILA MARIANA BONIFÁCIO DA SILVA GATTO', '275138/SP', 'SP', false, 'CNPJ', '61.493.311/0001-24', true, 'CAMILA MARIANA BONIFACIO DA SILVA GATTO LTDA Observação: CAMILA MARIANA SERVICOS MEDICOS', '61.493.311/0001-24');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('06a1c7b2-bea6-4203-9a9c-e1cd422efbdc'::uuid, 'DRA CAMILA PUPO MARIA', '58406/PR', 'PR', false, 'CPF', 'PENDENTE:PIX_EMAIL:camilapupo123@gmail.com', false, NULL, 'camilapupo123@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e48983f7-dd06-488f-9bbf-5afbc5ed97b5'::uuid, 'DRA CAMILA RODRIGUES DE AMORIM', '277240/SP', 'SP', false, 'CNPJ', '61.647.531/0001-65', true, 'CAMILA RODRIGUES DE AMORIM LTDA', '61.647.531/0001-65');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e0f16321-07a8-445d-8959-a469b6e81f83'::uuid, 'DRA CAROLINA MARCHETTI MORAES', '265270/SP', 'SP', false, 'CNPJ', '58.579.862/0001-09', true, 'MARCHETTI MORAES SERVICOS MEDICOS LTDA', '58.579.862/0001-09');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('054b8ab6-0d53-431d-b8bd-b025a0960ab3'::uuid, 'DRA CASSIA MARIA RAMALHO PERES', '24213/MG', 'MG', false, 'CPF', '523.230.566-20', true, NULL, '523.230.566-20');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('b4bb74b2-5186-4c95-a76b-d6d391bd51a2'::uuid, 'DRA CLARA HELENA FERREIRA GRILLO', '114027/MG', 'MG', false, 'CNPJ', '64.071.098/0001-50', true, 'FG CENTRO MEDICO LTDA', '64.071.098/0001-50');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('03862e2f-2604-4ce5-8b49-b1cee207f6d3'::uuid, 'DRA CLEIDE ALVES VALADARES', '70435/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(31) 97522-0368', false, NULL, '(31) 97522-0368');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('354156ff-48c7-417e-abcc-81f292f3dcbe'::uuid, 'DRA CRISTINA SAUTER LORENZONI', '61849/MG', 'MG', false, 'CPF', '716.242.601-87', true, NULL, '716.242.601-87');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('75cb39ec-b030-4630-8efd-4277ff638630'::uuid, 'DRA DAIANA MACEDO LOPO BORGES', '69084/MG', 'MG', false, 'CNPJ', '28.433.786/0001-50', true, 'DAIANA MACEDO L BORGES  Observação: 28.433.786/0001-50', '28.433.786/0001-50');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d5321fa2-1011-473a-a3be-7f1870a2c6a9'::uuid, 'DRA DANIELA MILO FERREIRA', '85443/MG', 'MG', false, 'CNPJ', '55.139.854/0001-45', true, 'Milo Ferreira Atendimento médico LTDA', '55.139.854/0001-45');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('175d0777-c28f-4df7-a61a-62a3102d30b1'::uuid, 'DRA DANIELLE NEVES', '278736/SP', 'SP', false, 'CNPJ', '63.188.653/0001-66', true, 'DANIELLE NEVES', '63.188.653/0001-66');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('40fd4b91-7a2b-4170-93dc-c5ac6bc2194c'::uuid, 'DRA DIRCE MARIA NOGUEIRA DA CRUZ COELHO', '91928/MG', 'MG', false, 'CPF', '333.015.147-15', true, NULL, '333.015.147-15');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('c36c44bd-0ad1-47a3-8ea8-c71086b3a606'::uuid, 'DRA EDUARDA GUARNIERI PEDRAO', '61032/PR', 'PR', false, 'CPF', 'PENDENTE:PIX_EMAIL:eduardaguarnieri.rd@gmail.com', false, NULL, 'eduardaguarnieri.rd@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('9d7c0998-ab94-4d0e-a496-77a1c10ee941'::uuid, 'DRA ELAINE FERREIRA SILVEIRA ZANON', '264013/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(13) 99755-1818', false, NULL, '(13) 99755-1818');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('1d02222d-bd2c-44f7-84b6-3f3da1c13d14'::uuid, 'DRA ELISA FRANCO GOIS SILVA', '279376/SP', 'SP', false, 'CNPJ', '64.111.809/0001-73', true, 'ELISA FRANCO SERVICOS MEDICOS LTDA', '64.111.809/0001-73');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e99b32dd-b140-440f-ac17-af215ea9572e'::uuid, 'DRA ELISANGELA FERRAZ PAZINATO', '91361/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_EMAIL:elisangelapazinato@gmail.com', false, NULL, 'elisangelapazinato@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('2bb97a45-b96e-435a-8220-10002507d0dd'::uuid, 'DRA ELISÂNGELA FUMAGALI GEROLINO', '62115/PR', 'PR', false, 'CPF', '033.591.069-62', true, NULL, '033.591.069-62');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('42c8ac39-62e4-490b-99f6-3814a22e484c'::uuid, 'DRA ELLEN ROSSI PATUCCI', '60490/PR', 'PR', false, 'CNPJ', '58.514.938/0001-00', true, 'PATUCCI SERVICOS EM SAUDE LTDA', '58.514.938/0001-00');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('69d33d91-3fc1-4a49-9afe-ef673b595304'::uuid, 'DRA ERICA BALBINO DA SILVA SALGADO', '45042/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 98812-6960', false, NULL, '(38) 98812-6960');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('f74f8852-8de3-4e00-be02-bbf14530626b'::uuid, 'DRA FERNANDA ANDRADE COSTA', '93942/MG', 'MG', false, 'CNPJ', '49.059.301/0001-80', true, 'FERNANDA ANDRADE COSTA', '49.059.301/0001-80');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d60a0de0-dc3d-41c8-8e76-0d89483fa402'::uuid, 'DRA FLAVIA FIORIN SPRONE', '282131/SP', 'SP', false, 'CNPJ', '63.811.148/0001-26', true, 'SPRONE SERVICOS MEDICOS LTDA', '63.811.148/0001-26');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a53b0df8-dea4-4c8c-a4a1-baa2ba9aa009'::uuid, 'DRA GABRIELA ALVES MIRANDA DAMACENO', '247111/SP', 'SP', false, 'CPF', '123.460.776-07', true, NULL, '123.460.776-07');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a40cac7c-cea4-40fa-890b-bc40e66897a7'::uuid, 'DRA GABRIELA AMORIM DA MOTA SILVERIO', '35033/DF', 'DF', false, 'CNPJ', '63.824.466/0001-21', true, 'CLINICA DRA. GABRIELA MOTA LTDA Observação: 63.824.466/0001-21', '63.824.466/0001-21');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e8d9dece-a712-4b34-bdf4-70fa4098a371'::uuid, 'DRA GABRIELA STIVAL GOMES', '248589/SP', 'SP', false, 'CNPJ', '53.281.826/0001-32', true, 'G S G Assistencia Medica Ltda', '53.281.826/0001-32');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('db59c4e2-92b9-4f71-8ac2-4275a23131be'::uuid, 'DRA GEOVANA DE MELO MENDONÇA', '252039/SP', 'SP', false, 'CPF', '097.190.736-67', true, NULL, '097.190.736-67');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('6019d544-f21d-4723-b2a9-09f7418f25f7'::uuid, 'DRA GIOVANA SALIBA DE PAULA', '197273/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(14) 98130-8409', false, NULL, '(14) 98130-8409');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('56bb91f8-a778-4b02-a18c-c037a64358fa'::uuid, 'DRA GIOVANNA DIAS DE LIMA', '103141/SP', 'SP', false, 'CNPJ', '56.028.684/0001-94', true, 'GDL SERVICOS MEDICOS LTDA', '56.028.684/0001-94');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('8f8b917e-7cb1-4d29-a656-66c203c9f6d2'::uuid, 'DRA GIOVANNA KAORI ICOMA MANZI', '266602/SP', 'SP', false, 'CNPJ', '58.337.739/0001-73', true, 'GIOVANNA KAORI ICOMA MANZI LTDA Observação: GIOVANNA KAORI SERVICOS MEDICOS', '58.337.739/0001-73');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e0fa7dab-3616-40ad-b794-797779e83adc'::uuid, 'DRA HELENA MIGUEL DEIENNO', '273803/SP', 'SP', false, 'CNPJ', '62.318.207/0001-66', true, 'CLINICA MEDICA HELENA MIGUEL DEIENNO LTDA', '62.318.207/0001-66');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('80ec17b6-f382-4fbc-aeab-685018f05f41'::uuid, 'DRA ISABELA CAIRES SARTORI', '258549/SP', 'SP', false, 'CNPJ', '55.747.278/0001-19', true, 'ICSARTORI SERVICOS MEDICOS LTDA', '55.747.278/0001-19');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('2edad9c3-926a-4efe-9a70-715915868965'::uuid, 'DRA ISABELA FALDONI BENEDITO', '282226/SP', 'SP', false, 'CNPJ', '63.966.333/0001-90', true, 'Faldoni Serviços Médicos LTDA.', '63.966.333/0001-90');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('4a58dc03-e0ac-4de1-aa16-7dd356486f1d'::uuid, 'DRA ISABELA INGRID RAVAGNANI', '282228/SP', 'SP', false, 'CNPJ', '64.011.622/0001-06', true, 'RAVAGNANI SERVICOS MEDICOS LTDA', '64.011.622/0001-06');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('240e6154-b1f1-456b-ad8f-76b83d2a475b'::uuid, 'DRA ISABELLA FERREIRA MELLI', '78255/MG', 'MG', false, 'CPF', '095.617.926-64', true, NULL, '095.617.926-64');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('cd5e2d0c-0fc0-42ad-b6f4-7dc86009d3b4'::uuid, 'DRA ISADORA DE ARAUJO', '276304/SP', 'SP', false, 'CNPJ', '63.022.135/0001-78', true, 'ISADORA DE ARAUJO', '63.022.135/0001-78');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('9c63bcba-cb48-4fd3-a8f4-0d5479e89b26'::uuid, 'DRA JADE RODRIGUES LINO DE OLIVEIRA', '81287/MG', 'MG', false, 'CPF', '083.335.376-42', true, NULL, '083.335.376-42');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('7d41a7e0-3d71-4b65-9a74-84959fbc89fc'::uuid, 'DRA JANE MARY GUEVARA MARTINS', '242054/SP', 'SP', false, 'CNPJ', '47.145.783/0001-65', true, 'J M G MARTINS', '47.145.783/0001-65');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('2db24298-fba0-4c28-a338-2ea74ad9450d'::uuid, 'DRA JAQUELINE BARTIRA BRASIL FERNANDES', '155129/SP', 'SP', false, 'CPF', '214.051.258-88', true, NULL, '214.051.258-88');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e4044f32-7939-4f22-9f05-7f1b053209ba'::uuid, 'DRA JULIA ALVES DE OLIVEIRA', '273827/SP', 'SP', false, 'CNPJ', '60.482.766/0001-81', true, 'J ALVES DE OLIVEIRA MEDICINA E SAUDE LTDA', '60.482.766/0001-81');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('25394e49-e246-4b6b-93f0-7ef689ffc0a7'::uuid, 'DRA JULIA CAXITO SANGIOVANI', '111165/MG', 'MG', false, 'CNPJ', '61.236.738/0001-47', true, 'JULIA C SANGIOVANI LTDA Observação: 61.236.738/0001-47', '61.236.738/0001-47');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3def32e0-3f7e-455e-9ad9-eb18127e7c54'::uuid, 'DRA JULIA DE MELO GOMES SIMOES ALMEIDA', '105637/MG', 'MG', false, 'CNPJ', '58.084.069/0001-20', true, 'JULIA MELO SERVICOS MEDICOS LTDA', '58.084.069/0001-20');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('7d6fe736-511f-43b7-bc18-23f9163a3179'::uuid, 'DRA JUSSIMAR MARIA GOBBI BENAZI DE OLIVEIRA', '59884/SP', 'SP', false, 'CNPJ', '04.557.398/0001-12', true, 'JORD SERVIÇOS MEDICOS E HOSPITALARES', '04.557.398/0001-12');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('6f35d53a-4909-46f0-8904-87951efcc9ba'::uuid, 'DRA KAMILA AZEVEDO SOUZA', '62833/MG', 'MG', false, 'CNPJ', '43.131.383/0001-40', true, 'AZEVEDO SOUZA SERVICOS MEDICOS LTDA', '43.131.383/0001-40');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('f9f707f6-d0e6-4c82-9b37-3ba58159ff0c'::uuid, 'DRA KATHLEEN RUSSI', '56695/PR', 'PR', false, 'CPF', '418.178.478-99', true, NULL, '418.178.478-99');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('49bdc115-dddf-4314-8162-5d265ecef570'::uuid, 'DRA LARA CAROLINA SAGANSKI', '61851/PR', 'PR', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(44) 98802-0803', false, NULL, '(44) 98802-0803');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('347211f9-3a64-404a-a8b8-8edb5690bdf1'::uuid, 'DRA LARA MARIA LUZ SOUZA', '266733/SP', 'SP', false, 'CNPJ', '58.857.508/0001-90', true, 'LARA LUZ LTDA Observação: PIX - PJ', '58.857.508/0001-90');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('cd32c91b-bb0e-4efe-93d9-99fa8e73376f'::uuid, 'DRA LARA MAZINI ROSSI', '264211/SP', 'SP', false, 'CNPJ', '58.912.849/0001-11', true, 'LARA MAZINI ROSSI CLINICA MEDICA LTDA', '58.912.849/0001-11');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('02a16a8d-422c-4473-bf98-f9d5fc459305'::uuid, 'DRA LARISSA ALMEIDA DA SILVA', '266735/SP', 'SP', false, 'CNPJ', '58.493.562/0001-02', true, 'LARISSA ALMEIDA DA SILVA LTDA', '58.493.562/0001-02');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('2a647f5f-5455-4b9a-8029-5e9423599f17'::uuid, 'DRA LARISSA EMANOELLE GONÇALVES MARQUETTI', '268334/SP', 'SP', false, 'CNPJ', '59.023.173/0001-78', true, 'Larissa Marquetti Serviços Medicos Ltda', '59.023.173/0001-78');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('85c49073-8247-4855-a560-59ff45cefb9a'::uuid, 'DRA LAURA GUIMARÃES DE OLIVEIRA', '103840/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99916-8838', false, NULL, '(38) 99916-8838');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('4738d0a2-b4df-4bf1-9b92-9fb4e5eee38c'::uuid, 'DRA LAVINIA BRITO GONÇALVES', '283955/SP', 'SP', false, 'CNPJ', '64.784.166/0001-29', true, 'LB SERVICOS MEDICOS LTDA', '64.784.166/0001-29');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('6941c4d3-a191-4dfe-8629-f8d22f5ffd5d'::uuid, 'DRA LEANDRA DE LIMA ROSA', '272622/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_ALEATORIA:125c2814-d721-4e05-902d-f83812e2c227', false, NULL, '125c2814-d721-4e05-902d-f83812e2c227');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('595feab9-631c-4f5e-9526-7254c508b729'::uuid, 'DRA LEIA ERNANDES FERNANDES DE CASTRO', '247138/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(18) 99158-0190', false, NULL, '(18) 99158-0190');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('f8da8630-14e9-4909-b2ca-824fcbb2e46e'::uuid, 'DRA LETICIA NATSUMI KOGA', '261276/SP', 'SP', false, 'CNPJ', '57.829.999/0001-01', true, 'LNK SERVICOS MEDICOS LTDA', '57.829.999/0001-01');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('32398b7c-5726-4198-95f7-84d6bacef967'::uuid, 'DRA LIDIA PARANHOS SANTOS FERNANDES', '59143/MG', 'MG', false, 'CNPJ', '31.615.168/0001-35', true, 'INSTITUTO BONS FRUTOS LTDA', '31.615.168/0001-35');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('34b1595b-ad26-43a1-af3d-886727236d63'::uuid, 'DRA LILIAN DARLENE BELOTTI', '190343/SP', 'SP', false, 'CNPJ', '29.329.916/0001-71', true, 'BELOTTI & BELOTTI SERVIÇOS MÉDICOS LTDA', '29.329.916/0001-71');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('444e05dd-a934-4700-b0b4-3a7762593431'::uuid, 'DRA LIVIA MATIAS PIZA', '284006/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(35) 99274-0035', false, NULL, '(35) 99274-0035');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('874564ce-b477-438a-a928-adf5cad560d4'::uuid, 'DRA LIZ AMARAL DE BRITO', '227875/SP', 'SP', false, 'CPF', '442.948.538-08', true, NULL, '442.948.538-08');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('4fb847e6-ad15-483c-ba5d-e1ccb2979f07'::uuid, 'DRA LORENA ALCEBIADES BORGES', '105638/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99848-5812', false, NULL, '(38) 99848-5812');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('6576503b-8c87-4c67-a0e2-0d5311ca6b42'::uuid, 'DRA LUÍSA DE OLIVEIRA E SILVA', '52260/RS', 'RS', false, 'CPF', 'PENDENTE:PIX_EMAIL:luisaoliveirasilva183@gmail.com', false, NULL, 'luisaoliveirasilva183@gmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('210873a8-b47d-4ff7-84cd-3d7640b27c6b'::uuid, 'DRA LUISA MAZZEO BUCHARA IORA', '267502/SP', 'SP', false, 'CNPJ', '60.099.889/0001-38', true, 'LUISA MAZZEO BUCHARA IORA LTDA', '60.099.889/0001-38');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e6d81665-14d6-48b9-8939-92207164b491'::uuid, 'DRA MARIA CAROLINA GUIMARÃES CASACA', '223259/SP', 'SP', false, 'CPF', '425.009.168-63', true, NULL, '425.009.168-63');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a3fa7508-9c8f-45a1-9e14-0e36bc5d306c'::uuid, 'DRA MARIA EDUARDA CORREA GODOY', '278504/SP', 'SP', false, 'CNPJ', '64.005.749/0001-04', true, 'MARIA EDUARDA CORREA GODOY LTDA', '64.005.749/0001-04');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('91da98fd-0dc3-44e0-949a-9f1aa318837e'::uuid, 'DRA MARIA EDUARDA DE MORAES VALVERDE', '63027/PR', 'PR', false, 'CNPJ', '64.146.110/0001-49', true, 'DE MORAES VALVERDE ATIVIDADE MEDICA LTDA', '64.146.110/0001-49');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('97acb1dc-dbbf-452e-9a5c-0fc8e6781618'::uuid, 'DRA MARIA EDUARDA PAES ROSA', '277112/SP', 'SP', false, 'CNPJ', '63.637.834/0001-22', true, 'THALLER PAES SERVICOS MEDICOS LTDA', '63.637.834/0001-22');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e01f56ec-b7ab-4051-bde4-c13931cdb940'::uuid, 'DRA MARIA EDUARDA QUEIROZ PEREIRA', '109509/MG', 'MG', false, 'CNPJ', '61.197.908/0001-21', true, 'MARIA EDUARDA QUEIROZ PEREIRA LTDA Observação: 61.197.908/0001-21', '61.197.908/0001-21');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('4d24fd39-285d-49b6-ae08-4549b32a91ba'::uuid, 'DRA MARIA EDUARDA ROSSETO SANTOS CARVALHO', '263438/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_EMAIL:Mariaarossetto@hotmail.com', false, NULL, 'Mariaarossetto@hotmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('43630398-447e-4691-adb9-af0838a5125c'::uuid, 'DRA MARIA JULIA ORTUÑO BORTOLOZZO', '273900/SP', 'SP', false, 'CNPJ', '61.289.533/0001-20', true, 'DRA MARIA JULIA ORTUÑO BORTOLOZZO', '61.289.533/0001-20');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3f35e3b8-0a45-4196-830d-fd3ece40f1c8'::uuid, 'DRA MARIA LUISA LEAO UEJO', '280555/SP', 'SP', false, 'CNPJ', '64.285.663/0001-82', true, 'UEJO SERVICOS MEDICOS LTDA', '64.285.663/0001-82');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('c905ae79-f13b-4e6e-ae54-bbfe4a258f69'::uuid, 'DRA MARIANA SCATOLIN PINATTI', '277508/SP', 'SP', false, 'CNPJ', '63.052.603/0001-57', true, 'PINATTI SERVICOS MEDICOS LTDA', '63.052.603/0001-57');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('5417266e-f604-4650-ae3e-1fbfc326ee54'::uuid, 'DRA MARIELLA FERREIRA MELLI', '93938/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99844-4588', false, NULL, '(38) 99844-4588');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('0a7611ce-396e-48df-a458-ba1d07cc0756'::uuid, 'DRA MARIELLE COSTA MACIEL', '105876/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 98821-0015', false, NULL, '(38) 98821-0015');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('af659cd8-a09b-4f7d-b382-d436adde6fbe'::uuid, 'DRA MARILIA VILELA MASSON', '203270/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_EMAIL:aiamasson@hotmail.com', false, NULL, 'aiamasson@hotmail.com');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d744caa6-2d1f-4852-8c3e-9d7362e17687'::uuid, 'DRA MAYARA HERRERO DE FREITAS', '280156/SP', 'SP', false, 'CNPJ', '64.200.758/0001-56', true, 'MAYARA HERRERO DE FREITAS LTDA', '64.200.758/0001-56');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a3dc021c-9767-45af-a4a0-6f878be9a9b5'::uuid, 'DRA MERKIA MACHADO TOLEDO', '29526/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99961-2304', false, NULL, '(38) 99961-2304');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('503aa578-9b42-4794-9c72-8f2a2b054b94'::uuid, 'DRA NATHÁLYA BARBOSA NAVARRO', '1128272/RJ', 'RJ', false, 'CNPJ', '53.680.917/0001-40', true, 'CENTRO DE CUIDADOS EM OFTALMOLOGIA E DERMATOLOGIA LTDA', '53.680.917/0001-40');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('f9756ad2-caaa-4e98-bcec-6810fcf17c14'::uuid, 'DRA NAYARA GRACIANO DA SILVA', '85440/MG', 'MG', false, 'CNPJ', '30.954.819/0001-59', true, 'LUANA DE OLIVEIRA ALVES E CIA LTDA', '30.954.819/0001-59');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('c3dc05e9-36f3-4882-96f2-d4511bbf803d'::uuid, 'DRA NICOLE DIAS SBRISSA', '265695/SP', 'SP', false, 'CNPJ', '58.112.539/0001-12', true, 'NICOLE DIAS SBRISSA LTDA', '58.112.539/0001-12');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('0c5be8f7-38e2-4d5e-9f84-98606f39124d'::uuid, 'DRA PAOLA BELEN VARGAS ACRE', '256447/SP', 'SP', false, 'CNPJ', '62.096.842/0001-46', true, 'ASPB SERVICOS MEDICOS LTDA', '62.096.842/0001-46');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('27928a2a-ff4b-4940-9f9f-89445145be80'::uuid, 'DRA PAULA DUMAS FIGUEIREDO', '202150/SP', 'SP', false, 'CNPJ', '53.621.737/0001-98', true, 'DUMAS FIGUEIREDO LTDA', '53.621.737/0001-98');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3f92dd38-2f80-4c80-9235-ae481b6e04e1'::uuid, 'DRA RAFAELA PASCOAL DI LOLLO', '273945/SP', 'SP', false, 'CNPJ', '61.575.201/0001-01', true, 'RAFAELA LOLLO SERVICOS MEDICOS LTDA', '61.575.201/0001-01');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('f98b5595-75b3-4ebe-a4c3-7b6581f0d6fe'::uuid, 'DRA RAFAELA RIBEIRO FACCIOLI', '235219/SP', 'SP', false, 'CNPJ', '47.669.146/0001-98', true, 'RAFAELA RIBEIRO SAUDE LTDA', '47.669.146/0001-98');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('060b53c6-9b81-4289-b776-31ba600de41e'::uuid, 'DRA RAQUEL CAMARGOS BORGES', '87678/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99969-5838', false, NULL, '(38) 99969-5838');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('5b833d3b-0a3c-4336-9313-e6da52dbe6dd'::uuid, 'DRA RENATA JANUÁRIO GARCIA', '160885/SP', 'SP', false, 'CPF', '367.754.158-18', true, NULL, '367.754.158-18');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('2b09bad4-b468-403a-ac80-8f365beaac7f'::uuid, 'DRA SARAH LOPES TEIXEIRA', '280228/SP', 'SP', false, 'CNPJ', '64.338.666/0001-37', true, 'SL SERVICOS MEDICOS LTDA', '64.338.666/0001-37');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('3895b526-194e-4ca0-a8c4-d86ad65e4cd4'::uuid, 'DRA STHEFFANY OLIVEIRA GUIMARÃES MACIEL', '105858/MG', 'MG', false, 'CNPJ', '58.541.239/0001-59', true, 'SGM SERVICOS MEDICOS LTDA', '58.541.239/0001-59');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('e123e94e-bddd-4142-a723-265f8ff5c910'::uuid, 'DRA TALITA RAVAGNANI BISSON', '252697/SP', 'SP', false, 'CNPJ', '53.711.456/0001-26', true, 'QUI AMAT SERVICOS MEDICOS LTDA', '53.711.456/0001-26');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('482f5207-f731-4c44-ae11-05edc85593d2'::uuid, 'DRA TAOMÍ CANÇADO GUIMARÃES', '60760/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_ALEATORIA:71b8a9d9-d34c-4a6d-bd63-ad9005854ccf', false, NULL, '71b8a9d9-d34c-4a6d-bd63-ad9005854ccf');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('0c50a225-8451-43c8-b8d5-d1f6d5301859'::uuid, 'DRA TERESA CRISTINA CORRÊA FÁBREGA DE CARVALHO', '29873/SP', 'SP', false, 'CPF', '782.796.668-34', true, NULL, '782.796.668-34');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('c2b644ed-7d1b-47b5-bbe7-3efd208a02fe'::uuid, 'DRA THAIS CRIS UOLO CARDOSO', '151434/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(11) 96358-4557', false, NULL, '(11) 96358-4557');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('afd53e87-444a-4d22-86cf-db2e526531b6'::uuid, 'DRA THÁLITA CRISTINA DE SOUSA BEINE', '273031/SP', 'SP', false, 'CNPJ', '61.223.708/0001-04', true, 'Beine Medicina Ltda', '61.223.708/0001-04');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('bcc3c2b8-74e3-4f06-8962-5c748b76c9f4'::uuid, 'DRA THALITA SARGI MONTEDOR', '252723/SP', 'SP', false, 'CNPJ', '53.291.066/0001-44', true, 'TSM SERVIÇOS MEDICOS LTDA', '53.291.066/0001-44');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('02b01d94-2a3f-47ae-8c53-a10adeabdedc'::uuid, 'DRA THAYNA JACINTO NANCI', '257718/SP', 'SP', false, 'CPF', '470.845.678-60', true, NULL, '470.845.678-60');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d780e8d1-bd22-4595-88dd-e836ce3b9103'::uuid, 'DRA THUANE DE PAULA MATOS', '104820/MG', 'MG', false, 'CNPJ', '63.177.983/0001-56', true, 'CLINICA MEDICA SANTA CECILIA', '63.177.983/0001-56');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('da58d167-1d36-4cf6-a788-4f3b8d4484a0'::uuid, 'DRA VANESSA LEONARDI DAL VESCO', '56861/PR', 'PR', false, 'CPF', '045.884.569-89', true, NULL, '045.884.569-89');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('64c5d8d1-c7fe-4a8c-a459-201d73f1e393'::uuid, 'DRA VITORIA ZANIN ESCUZIATO', '268287/SP', 'SP', false, 'CNPJ', '58.919.841/0001-87', true, 'ZANIN ESCUZIATO CLINICA MEDICA LTDA', '58.919.841/0001-87');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('ef40c4fb-54c9-4695-ad3f-c6f233317755'::uuid, 'DRA VIVIAN CAVALCA SCANAGATTA', '272253/SP', 'SP', false, 'CNPJ', '59.871.165/0001-81', true, 'V SCANAGATTA SERVIÇOS MÉDICOS LTDA', '59.871.165/0001-81');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('97f1801a-5095-4709-874c-b41fc35eb065'::uuid, 'DRA YENNIS DIGNORA NUNEZ SANZ', '268682/SP', 'SP', false, 'CPF', '067.747.461-01', true, NULL, '067.747.461-01');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('b85f75af-6da1-44df-8ee1-fb662e5e06c1'::uuid, 'EDINALVA MACHADO DA SILVA', '00000000/MG', 'MG', false, 'CPF', '709.424.711-72', true, NULL, '709.424.711-72');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('d1b63acf-f5e8-4bb7-8789-8e6c92f170a2'::uuid, 'ERICA MACHADO DA SILVA', '000444705/MG', 'MG', false, 'CNPJ', '63.943.530/0001-93', true, 'ERICA MACHADO DA SILVA Observação: 63943530000193', '63.943.530/0001-93');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('8a6cf9ea-5439-474d-99d0-a488d7cdb09e'::uuid, 'FLAVIO SOUTO JUNIOR', '0000000000/PR', 'PR', false, 'CNPJ', '46.227.892/0001-69', true, 'FLAVIO SOUTO JUNIOR', '46.227.892/0001-69');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a2bdd159-28f2-4719-811c-1b3fd78e2fcf'::uuid, 'GERALDO FARIA CAMPOS JUNIOR', '00000000/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99978-6783', false, NULL, '(38) 99978-6783');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('994c29e8-caae-408e-b53a-7cd11b276991'::uuid, 'HORARIOS DE ALMOCO', '225689/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_AUSENTE:', false, NULL, NULL);
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('55c94a6e-4076-4db5-8d51-08dfabe9e45d'::uuid, 'IRLENE MARIA DA SILVA CASTRO', '00000000/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99998-9978', false, NULL, '(38) 99998-9978');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('aebaf6bd-e59e-42d7-8279-71d28d3bce3e'::uuid, 'KAROLINY DAIARA MARTINS  DE OLIVEIRA', '00000000/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 98834-4600', false, NULL, '(38) 98834-4600');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('a6495af4-a6d1-47b6-892b-e9531a3b1d04'::uuid, 'LEOMAR MILITÃO DA CUNHA', '331010/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 99917-1247', false, NULL, '(38) 99917-1247');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('988bc3a4-d4f3-486c-b0d1-dd19b17c8b23'::uuid, 'MARIA ELOISA OLIVEIRA NOVAES', '279045/SP', 'SP', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(11) 97086-1812', false, NULL, '(11) 97086-1812');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('4ee3ef18-211b-41f5-8b2e-5821803fbe85'::uuid, 'MARIA MEIRA AMARAL CRUZEIRO', '00000000/MG', 'MG', false, 'CPF', '944.070.376-87', true, NULL, '944.070.376-87');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('cbbd7d71-15b1-4fd4-bd71-ff19bc90174e'::uuid, 'MEDICO SPM', '0000000/PR', 'PR', true, 'CPF', 'PENDENTE:PIX_AUSENTE:', false, NULL, NULL);
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('196a9222-a373-4fc9-b676-eb0951b2c4f7'::uuid, 'MIRELLY APARECIDA ARAUJO GOMES', '925096/MG', 'MG', false, 'CPF', '144.209.016-24', true, NULL, '144.209.016-24');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('079144d0-f81a-4d7e-9a8d-3c28958a2aec'::uuid, 'PAMELA KARLA SILVA', '0000000/MG', 'MG', false, 'CPF', 'PENDENTE:PIX_TELEFONE:(38) 9998-8878', false, NULL, '(38) 9998-8878');
INSERT INTO prestador (id, nome, registro_profissional, uf, ficticio, tipo_doc, cpf_cnpj, cpf_cnpj_validado, razao_social_pj, chave_pix)
VALUES ('7fa67b00-ef02-474b-b780-5e79a364854a'::uuid, 'RAFAELA APARECIDA JOSLIN MENDES', '441.379/MG', NULL, false, 'CPF', '116.879.076-09', true, NULL, '116.879.076-09');

-- =====================================================
-- 4. CONTRATOS (115)
-- =====================================================
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('3df173e1-1ac4-45ff-943b-3fe9dfb173c0'::uuid, 'MG - UNAI - SESAU - ADMINISTRATIVO - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - SESAU - ADMINISTRATIVO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('023db8d5-c25c-43cc-ab75-ab1b9cbbd371'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - MANCHESTER - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - MANCHESTER - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('4bb28819-fee4-487d-8269-7508cdb01849'::uuid, 'SP – SERTÃOZINHO – UBS JAMAICA - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP – SERTÃOZINHO – UBS JAMAICA - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CLINICA MÉDICA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CLINICA MÉDICA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('8e23ba4f-47c0-40c9-9202-407cca002957'::uuid, 'MG - UNAI - POLICLINICA - PSIQUIATRIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - PSIQUIATRIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('b713ae3e-aae6-4264-8a29-83642689d0f9'::uuid, 'SP – SERTÃOZINHO - SAMU - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP – SERTÃOZINHO - SAMU - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('9c396be8-eba8-4f64-82af-acc6762b997c'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - ORTOPEDIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - ORTOPEDIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('127d4f8f-5026-4839-ae7a-94f4a9587547'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA GERAL MEDIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA GERAL MEDIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('6d1e7db3-1a98-4c20-aa96-1f4bde7ee901'::uuid, 'MG - UNAI - POLICLINICA - ORTOPEDIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - ORTOPEDIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('66547848-64b1-4b3d-82aa-53101b319000'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA ORTOPEDICA MEDIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA ORTOPEDICA MEDIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('66807f9a-30dd-457e-9207-55ab5a10e0f9'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - AUXILIO CIRURGICO - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - AUXILIO CIRURGICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('17331cc8-9aa7-4df5-a39b-a38ab32d3bee'::uuid, 'MG - UNAI - HOSPITAL SANTA MONICA - ATENDIMENTO EM ORTOPEDIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL SANTA MONICA - ATENDIMENTO EM ORTOPEDIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('cdb4c8de-e8ba-4612-8701-241b10eb8042'::uuid, 'PR - CISMEPAR - IBIPORÃ - UPA - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - IBIPORÃ - UPA - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('eadcd43d-94b4-4a91-a565-02dde3a46310'::uuid, 'PR - CISMEPAR - CAMBÉ - PA 24H - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - CAMBÉ - PA 24H - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('3404182d-e4b1-4366-89fe-109aab61aba7'::uuid, 'SP – SERTÃOZINHO – UVBS SANTA ROSA - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP – SERTÃOZINHO – UVBS SANTA ROSA - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('9dcc6814-28e4-441d-9e92-da44a121535c'::uuid, 'SP - SERTAOZINHO - UBS SHANGRI-LA -  PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP - SERTAOZINHO - UBS SHANGRI-LA -  PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('75d78964-5e1e-4856-9475-d62661b2215b'::uuid, 'SP - SERTAOZINHO - SAD - PSF - SPM', 'PUBLICO', 'ATIVO', 'SP - SERTAOZINHO - SAD - PSF - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, 'SP – SERTÃOZINHO – UBS CRUZ DAS POSSES - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP – SERTÃOZINHO – UBS CRUZ DAS POSSES - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('5a891672-43d7-46b2-9581-79260491814f'::uuid, 'SP – SERTÃOZINHO – PAQUE ECOLOGICO - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP – SERTÃOZINHO – PAQUE ECOLOGICO - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('24cf60c6-bfb0-4b33-9a67-302ea1c78910'::uuid, 'PR - HOSPITAL CRISTO REI - IBIPORÃ - SUPORTE PED - SPM', 'PUBLICO', 'ATIVO', 'PR - HOSPITAL CRISTO REI - IBIPORÃ - SUPORTE PED - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('6a305177-6f47-4ac0-85e7-e137619257bf'::uuid, 'PR - HOSPITAL CRISTO REI - IBIPORÃ - PLANTONISTA INFANTIL - SPM', 'PUBLICO', 'ATIVO', 'PR - HOSPITAL CRISTO REI - IBIPORÃ - PLANTONISTA INFANTIL - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('35ca30ef-1db0-4b32-8970-f863e834a71a'::uuid, 'PR - CISMEPAR - LONDRINA - PAI - PLANTONISTA CLINICO INFANTIL - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - LONDRINA - PAI - PLANTONISTA CLINICO INFANTIL - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('5c686592-4e2c-4865-9431-05581f02d7a2'::uuid, 'PR - CISMEPAR - CAMBÉ - UPA - PLANTONISTA INFANTIL - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - CAMBÉ - UPA - PLANTONISTA INFANTIL - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('4ca7cd02-691c-4a64-b0ea-d5d20ede3941'::uuid, 'PR - LONDRINA - PAI (CHAMAMENTO) - ATENDIMENTO INFANTIL - SPM', 'PUBLICO', 'ATIVO', 'PR - LONDRINA - PAI (CHAMAMENTO) - ATENDIMENTO INFANTIL - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('daed2614-db01-4ca9-8926-67eb0069c301'::uuid, 'MG - UNAI - POLICLINICA - NEURO PEDIATRIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - NEURO PEDIATRIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CLINICA MÉDICA HORIZONTAL - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CLINICA MÉDICA HORIZONTAL - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, 'MG - UNAI - SPA - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - SPA - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('124417e6-78df-46d0-a70b-8e597c7006c6'::uuid, 'MG - UNAI - REGULAÇÃO - REUGULAÇÃO - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - REGULAÇÃO - REUGULAÇÃO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('e52ab2e4-3351-42e5-91b0-721658014c5e'::uuid, 'MG - UNAI - SEDE SPM - COORDENAÇÃO MEDICA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - SEDE SPM - COORDENAÇÃO MEDICA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('1f148982-eb29-411e-8be5-fb89c1b14f8c'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - HORIZONTAL SALA DE PARTO - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - HORIZONTAL SALA DE PARTO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('cb6d919e-2293-4555-9088-a502404df079'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - PEDIATRIA URGENCIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - PEDIATRIA URGENCIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('1f8f1790-40a3-49da-bc7f-53bcdaf32dd0'::uuid, 'PR - CISMEPAR - LONDRINA - PA MARIA CECÍLIA - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - LONDRINA - PA MARIA CECÍLIA - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('9f2d4706-1589-422c-9c85-d1f54af507a6'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA GERAL - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA GERAL - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('8a5282fd-7b46-40dc-bdb3-3a8a9023c109'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - INSTRUMENTADOR - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - INSTRUMENTADOR - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('af990d28-a209-4907-9dcf-8477a87a77d5'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO - CIRURGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO - CIRURGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('f852e91d-aaea-4624-952d-f38c2f73a9b6'::uuid, 'MG - UNAI - POLICLINICA - UROLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - UROLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('6bec2577-b724-44e3-9b67-a8ddc211d3da'::uuid, 'MG - UNAI - POLICLINICA - CIRURGIA GERAL - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - CIRURGIA GERAL - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('69450eea-dd25-4f21-ada2-42d0bc0142ef'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA UROLOGICA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA UROLOGICA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('be00c4ba-86dc-4752-a727-01dc65bf664d'::uuid, 'SP - SANTA CASA - PARAGUAÇU PAULISTA - PEDIATRIA - SPM', 'PUBLICO', 'ATIVO', 'SP - SANTA CASA - PARAGUAÇU PAULISTA - PEDIATRIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('4beab894-ce34-4475-a5e0-6b7fce7387f6'::uuid, 'MG - UNAI - POLICLINICA - OFTALMOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - OFTALMOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('1e7ffac2-e617-41fd-bad2-eae8077dc5fe'::uuid, 'MG - TOLEDO - UBS MISTA - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'MG - TOLEDO - UBS MISTA - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('17606b42-4f1a-44ef-a09c-932e234a8ccf'::uuid, 'SP - BERTIOGA - CAPS - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA - CAPS - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('404cbf03-f768-4029-9451-7d9303df9679'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - ANESTESIA URGENCIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - ANESTESIA URGENCIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('489dd2a6-de7d-46ca-b08b-c56f789b71cc'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - ANESTESIA ELETIVA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - ANESTESIA ELETIVA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('11c9b64b-e9c5-40b2-9e9f-9dc0fdc2f5db'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO -  ANESTESIA', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO -  ANESTESIA');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, 'SP – SERTÃOZINHO – UBS ALVORADA - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP – SERTÃOZINHO – UBS ALVORADA - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('7bcefc0d-03eb-44f2-9329-124e4a5ad8fe'::uuid, 'MG - TOLEDO - UBS MISTA - PEDIATRIA - PLANTÃO - SPM', 'PUBLICO', 'ATIVO', 'MG - TOLEDO - UBS MISTA - PEDIATRIA - PLANTÃO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('6c462ca9-f819-45c3-bdd0-82353ea51d9c'::uuid, 'MG - UNAI - POLICLINICA - ENDOCRINOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - ENDOCRINOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('02b16232-c617-4c05-b26e-7ec04a165278'::uuid, 'PR - TAMARANA - HOSPITAL SÃO FRANCISCO - PLANTONISTA CLINICO - PREFEITURA - SPM', 'PUBLICO', 'ATIVO', 'PR - TAMARANA - HOSPITAL SÃO FRANCISCO - PLANTONISTA CLINICO - PREFEITURA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('030dddcf-8d69-4749-bd0d-e30a0bf5a009'::uuid, 'MG - UNAI - SESAU - PEDIATRIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - SESAU - PEDIATRIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('0f363f4a-0b1d-486f-86c7-61939a69ec13'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - GINECOLOGIA/OBSTETRICIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - GINECOLOGIA/OBSTETRICIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('8f2b2dd1-268e-477c-991d-dbebad7cb709'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA GINECOLOGICA PEQUENA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA GINECOLOGICA PEQUENA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('b4a4e021-8e8b-4b6d-8ea7-5290d4bcdac5'::uuid, 'MG - UNAI - SESAU - GINECOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - SESAU - GINECOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('a5c4dc0d-fcfc-48c9-a3e8-99a50a7013cd'::uuid, 'MG - UNAI - SESAU - PRÉ-NATAL DE RISCO HABITUAL - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - SESAU - PRÉ-NATAL DE RISCO HABITUAL - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('f0092b86-a6be-4c67-9ac2-b8087af63008'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA GINECOLOGICA MEDIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA GINECOLOGICA MEDIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, 'SP - SANTA CASA - PARAGUAÇU PAULISTA - PS- PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP - SANTA CASA - PARAGUAÇU PAULISTA - PS- PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('2f30cf19-9676-4a05-a2f5-3abbda0ae2e4'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO -  GINECOLOGIA E OBSTETRICIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO -  GINECOLOGIA E OBSTETRICIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('47bf28e5-972d-48ca-addb-56bf89eb406a'::uuid, 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM NEUROPEDIATRIA', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM NEUROPEDIATRIA');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, 'SP – SERTÃOZINHO – UBS COHAB III - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP – SERTÃOZINHO – UBS COHAB III - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('ca6b8a69-a923-4d38-975c-4eb7fbbf2c7a'::uuid, 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO ORTOPEDIA - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO ORTOPEDIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('045fd18d-2103-413d-8c1d-a3ba59510253'::uuid, 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM NEUROLOGIA - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM NEUROLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('d81a4bf9-0be7-49d6-9330-130cbedeaca6'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA GERAL PEQUENA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CIRURGIA GERAL PEQUENA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('0663cef7-cdf5-4ec1-9916-8aba60fc0c20'::uuid, 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM CARDIOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM CARDIOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('d29229cb-15ee-46a6-986f-129a96367659'::uuid, 'MG - TOLEDO - UBS MISTA - CARDIOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - TOLEDO - UBS MISTA - CARDIOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('c40743d3-a4b6-4061-ac12-c5b6a5e43a34'::uuid, 'PR - MANDIRITUBA - HOSPITAL MUNICIPAL - PLANTONISTA CLINICO', 'PUBLICO', 'ATIVO', 'PR - MANDIRITUBA - HOSPITAL MUNICIPAL - PLANTONISTA CLINICO');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('72e3c253-8b52-4bd5-9b72-48b067286bb6'::uuid, 'SP - BERTIOGA – CENTRO DE ATENÇÃO PSICOSSOCIAL – C - ATENDIMENTO EM PSIQUIATRIA - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – CENTRO DE ATENÇÃO PSICOSSOCIAL – C - ATENDIMENTO EM PSIQUIATRIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('2518a12a-480e-49b7-a3f4-2fbdad3dce7b'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - NEUROLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - NEUROLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('25541751-40c8-498f-9e22-b797c1714e8e'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO - ORTOPEDIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO - ORTOPEDIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('94e38e26-60a0-4108-8332-5c7e02d83f50'::uuid, 'SP – SERTÃOZINHO – UBS COHAB VIII - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP – SERTÃOZINHO – UBS COHAB VIII - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('4c614b42-3f87-481f-9b22-8167a56c1c25'::uuid, 'SP - SANTA CASA - PARAGUAÇU PAULISTA - PS- PLANTONISTA CLINICO EMERGEN. E URGÊNCIA  - SPM', 'PUBLICO', 'ATIVO', 'SP - SANTA CASA - PARAGUAÇU PAULISTA - PS- PLANTONISTA CLINICO EMERGEN. E URGÊNCIA  - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('8fe43bf7-3261-4336-a4e9-a58b5ef3c366'::uuid, 'SP – BERTIOGA – CENTRO DE INFECT. BERTIOGUENSE - ATENDIMENTO EM INFECTOLOGIA PEDIATRA - SPM', 'PUBLICO', 'ATIVO', 'SP – BERTIOGA – CENTRO DE INFECT. BERTIOGUENSE - ATENDIMENTO EM INFECTOLOGIA PEDIATRA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('19aa0b12-e9c5-4a85-b462-a6b599f9e349'::uuid, 'SP - MACAUBAL - UBS CENTRAL - ATENDIMENTO EM PSIQUIATRIA - SPM', 'PUBLICO', 'ATIVO', 'SP - MACAUBAL - UBS CENTRAL - ATENDIMENTO EM PSIQUIATRIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('db9f68ca-be04-4765-bb45-4f2c49309c7a'::uuid, 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM ALERGOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM ALERGOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('1ce72d39-e901-4750-b758-f9e3b58d75ae'::uuid, 'SP - SANTA CASA - PARAGUAÇU PAULISTA - DIRETOR CLINICO PS - SPM', 'PUBLICO', 'ATIVO', 'SP - SANTA CASA - PARAGUAÇU PAULISTA - DIRETOR CLINICO PS - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('080a8741-1d8d-432f-9bf6-3e36b06700bc'::uuid, 'MG - UNAI - POLICLINICA - GATROENTEROLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - GATROENTEROLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('db769249-13d3-4d83-9fb5-93fcb39d5819'::uuid, 'PR - LUNARDELLI - CENTRO DE SAUDE -  ESF - SPM', 'PUBLICO', 'ATIVO', 'PR - LUNARDELLI - CENTRO DE SAUDE -  ESF - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('b26c91bf-43ed-4e98-80a6-288b83a110df'::uuid, 'PR - CALIFORNIA - CENTRO DE SAUDE 24HRS - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - CALIFORNIA - CENTRO DE SAUDE 24HRS - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('d73faddc-610e-484e-8851-23d808738f83'::uuid, 'MG - TOLEDO - UBS MISTA - GINECOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - TOLEDO - UBS MISTA - GINECOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('8d828bde-3a22-461c-888d-d8612fdfb910'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - PEDIATRIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - PEDIATRIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('67de2622-d5e7-4c74-af02-27424750c07c'::uuid, 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO CIRURGIA GERAL/GASTRO - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO CIRURGIA GERAL/GASTRO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('6e0c2495-0bf8-4698-bef4-eab8562e22e7'::uuid, 'PR - JURANDA - UBS NOSSA SENHORA DA MÃE DE DEUS - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - JURANDA - UBS NOSSA SENHORA DA MÃE DE DEUS - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('15472bd9-a182-45ce-983e-c1579da653ea'::uuid, 'MG - UNAI - POLICLINICA - CLÍNICA MÉDICA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - CLÍNICA MÉDICA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('f2da6473-d7db-4cef-bdfc-de7867836797'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - EXAMES - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - EXAMES - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('4c892f40-4cfb-436f-8221-8320dd465b09'::uuid, 'MG - TOLEDO - UBS MISTA - RADIOLOGIA GERAL - SPM', 'PUBLICO', 'ATIVO', 'MG - TOLEDO - UBS MISTA - RADIOLOGIA GERAL - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('29f3be09-dca5-42bb-b658-2ce133b3fb96'::uuid, 'PR - CISMEPAR - LONDRINA - UPA SABARÁ - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - LONDRINA - UPA SABARÁ - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('77c23072-16a4-48bd-a1fc-308cdeace495'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO - CLINICA MEDICA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO - CLINICA MEDICA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('97ed68fd-e2a3-447b-b5cc-3b66cf29626f'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CARDIOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - CARDIOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('2e9b5517-eeb3-47d2-afe5-619ac0ef9a20'::uuid, 'MG - UNAI - POLICLINICA - CARDIOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - CARDIOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('c590b3f7-87d4-4c06-a6ae-14fa232b9ecc'::uuid, 'MG - UNAI - CAPS - ATENDIMENTO EM PSIQUITRIA', 'PUBLICO', 'ATIVO', 'MG - UNAI - CAPS - ATENDIMENTO EM PSIQUITRIA');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('9960c157-9313-410d-a2cf-471eb688a51f'::uuid, 'MG - UNAI - CAPS - ATENDIMENTO EM CLINICA MEDICA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - CAPS - ATENDIMENTO EM CLINICA MEDICA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('f6b9f9b7-14cb-4ced-aebe-8d076e4a775f'::uuid, 'MG - UNAI - POLICLINICA - DERMATOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - DERMATOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('d25690c8-54c1-4bdb-b0da-00bb6f7353d1'::uuid, 'MG - UNAI - POLICLINICA - PNEUMOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - PNEUMOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('59715aba-3102-44d5-b7c2-b5323fefb7c3'::uuid, 'SP - SERTAOZINHO - UBS ALTO DO GINASIO - ATENDIMENTO CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP - SERTAOZINHO - UBS ALTO DO GINASIO - ATENDIMENTO CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('dc235b47-5ef4-48e7-ad0b-1664b3bfa44b'::uuid, 'MG - TOLEDO - UBS MISTA - PEDIATRIA - AMBULATORIO - SPM', 'PUBLICO', 'ATIVO', 'MG - TOLEDO - UBS MISTA - PEDIATRIA - AMBULATORIO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('15df1ff2-5ade-4c74-b856-7a81443370db'::uuid, 'MG - UNAI - CAPS - ATENDIMENTO EM PSIQUIATRIA (AD) - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - CAPS - ATENDIMENTO EM PSIQUIATRIA (AD) - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('4fcdbed0-9539-4bb7-a29f-5812abcf04f3'::uuid, 'MG - UNAI - SAME - INFECTOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - SAME - INFECTOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('f7dca287-f378-4eaa-9a3d-e90b5f102a43'::uuid, 'PR - CISMEPAR - JATAIZINHO - UBS CENTRAL - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - JATAIZINHO - UBS CENTRAL - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('020eb4cf-2d63-4ab0-9eea-617ac0cb345c'::uuid, 'PR - CISMEPAR - LONDRINA - PA LEONOR - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - LONDRINA - PA LEONOR - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('53f83a95-0f93-462f-896e-d605d07859d0'::uuid, 'PR - CISMEPAR - CAMBÉ - UPA - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - CAMBÉ - UPA - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('edec0dd8-4cb2-4b27-b8a0-f55b6e7d154a'::uuid, 'PR - CISMEPAR - LONDRINA - PA UNIÃO DA VITÓRIA - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - LONDRINA - PA UNIÃO DA VITÓRIA - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('f350d63f-712a-457d-8272-27c87ac0351c'::uuid, 'SP - BERTIOGA - ESF BORACÉIA - MÉDICOS PLANTONISTAS - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA - ESF BORACÉIA - MÉDICOS PLANTONISTAS - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('eb895306-d199-42c0-936d-49503131bfb0'::uuid, 'MG - UNAI - HOSPITAL SANTA MONICA - ATENDIMENTO EM NEUROLOGIA  - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL SANTA MONICA - ATENDIMENTO EM NEUROLOGIA  - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('bc883f46-6d9e-44ad-94a4-3c25fe2b4bdd'::uuid, 'MG - UNAI - POLICLINICA - NEUROLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - NEUROLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('f4264e3e-d79a-42eb-baf1-d6a2e3f0b442'::uuid, 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM ENDOCRINOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM ENDOCRINOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('406cbb47-ab51-445e-a5d2-e6a36f6634ef'::uuid, 'SP - ASPASIA - UBS - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP - ASPASIA - UBS - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('85f5634b-85c3-4559-8dc1-cba7bc79e631'::uuid, 'MG - UNAI - POLICLINICA - MASTOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - MASTOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('6eeb2a2f-e3af-4ba8-834d-f747c86ac9a9'::uuid, 'PR - CISMEPAR - LONDRINA - UPA CENTRO OESTE - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'PR - CISMEPAR - LONDRINA - UPA CENTRO OESTE - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('4fc2ee21-316c-4137-aa7f-397d056f99c9'::uuid, 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM CIRURGIA VASCULAR - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM CIRURGIA VASCULAR - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('2cc4f825-95f3-4c2a-a906-a26bd7539a5f'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO - PEDIATRIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - COORDENAÇÃO - PEDIATRIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('21e3591c-c081-40ba-af15-8403a2848176'::uuid, 'MG - UNAI - POLICLINICA - REUMATOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - POLICLINICA - REUMATOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('52b14bfd-b2b3-4b2c-babd-d7bdf69871ab'::uuid, 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM PNEUMOLOGIA - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - ATENDIMENTO EM PNEUMOLOGIA - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('5c18756e-e633-484a-ad30-632d81ddcc41'::uuid, 'SP - BERTIOGA - CENTRAL DE REGULAÇÃO - PLANTONISTA CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA - CENTRAL DE REGULAÇÃO - PLANTONISTA CLINICO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('729f4582-745e-4770-ac22-4e40d82d76a7'::uuid, 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - ADMINISTRATIVO - SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - HOSPITAL MUNC. DR JOAQUIM BROCHADO - ADMINISTRATIVO - SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('8c4b9ed2-9c36-4f3f-bc1c-296abdadf618'::uuid, 'MG - UNAI - SEDE SPM - ADMINISTRATIVO -SPM', 'PUBLICO', 'ATIVO', 'MG - UNAI - SEDE SPM - ADMINISTRATIVO -SPM');
INSERT INTO contrato (id, nome, tipo, status, local_pp)
VALUES ('97c3137d-1cf8-4a83-ad7b-18d6619f050f'::uuid, 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - DIRETOR CLINICO - SPM', 'PUBLICO', 'ATIVO', 'SP - BERTIOGA – UNI. BERTIOGUENSE DE ESP. MÉD UNIB - DIRETOR CLINICO - SPM');

-- =====================================================
-- 5. EXCECOES PJ (3)
-- =====================================================
INSERT INTO excecao_pj (prestador_id, razao_social_autorizada, cnpj, data_aprovacao, justificativa, aprovado_por)
VALUES ('86f2c3ea-4c76-438d-b37c-a974dfc08f78'::uuid, 'CLINICA DR FABIO SOUZA', NULL, '2026-04-15', 'Validada em sessao Claude.ai 15/04/2026', '09ac0652-a1f1-467c-b072-33dc1f740fd7'::uuid);
INSERT INTO excecao_pj (prestador_id, razao_social_autorizada, cnpj, data_aprovacao, justificativa, aprovado_por)
VALUES ('5158f26f-4e3f-445e-8979-902d4369bb11'::uuid, 'GLENIO NEIVA JORDAO S', NULL, '2026-04-15', 'Validada em sessao Claude.ai 15/04/2026', '09ac0652-a1f1-467c-b072-33dc1f740fd7'::uuid);
INSERT INTO excecao_pj (prestador_id, razao_social_autorizada, cnpj, data_aprovacao, justificativa, aprovado_por)
VALUES ('f9756ad2-caaa-4e98-bcec-6810fcf17c14'::uuid, 'LUANA DE OLIVEIRA ALVES E CIA LTDA', '30.954.819/0001-59', '2026-04-14', 'Validada antes de 15/04/2026. CNPJ confirmado em sessao 17/04.', '09ac0652-a1f1-467c-b072-33dc1f740fd7'::uuid);

-- =====================================================
-- 6. REGISTRO_PP (374)
-- =====================================================
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('86fe9648-3b7c-4b65-98aa-7c65a07b6189'::uuid, '3df173e1-1ac4-45ff-943b-3fe9dfb173c0'::uuid, '2026-02', 5000.04, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f0dfc745-4322-4e3e-acbb-907809ff4eee'::uuid, '023db8d5-c25c-43cc-ab75-ab1b9cbbd371'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5176f65e-b9d7-492a-a449-5457dddd8d94'::uuid, '4bb28819-fee4-487d-8269-7508cdb01849'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('97fdb7fb-f017-47d2-8539-549d43cce144'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 11050.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('60db1059-519f-420d-acf4-89526f4da899'::uuid, '8e23ba4f-47c0-40c9-9202-407cca002957'::uuid, '2026-02', 15785.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ad694ac4-8e54-4aca-86cb-75fb8f63b920'::uuid, 'b713ae3e-aae6-4264-8a29-83642689d0f9'::uuid, '2026-02', 15380.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('0daee7dd-568c-40a3-b94a-b472d81a147f'::uuid, '9c396be8-eba8-4f64-82af-acc6762b997c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('0daee7dd-568c-40a3-b94a-b472d81a147f'::uuid, '127d4f8f-5026-4839-ae7a-94f4a9587547'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('0daee7dd-568c-40a3-b94a-b472d81a147f'::uuid, '6d1e7db3-1a98-4c20-aa96-1f4bde7ee901'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('0daee7dd-568c-40a3-b94a-b472d81a147f'::uuid, '66547848-64b1-4b3d-82aa-53101b319000'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('0daee7dd-568c-40a3-b94a-b472d81a147f'::uuid, '66807f9a-30dd-457e-9207-55ab5a10e0f9'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('0daee7dd-568c-40a3-b94a-b472d81a147f'::uuid, '17331cc8-9aa7-4df5-a39b-a38ab32d3bee'::uuid, '2026-02', 1400.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('4803fdc2-7108-4d8c-b56e-9ca7f1819523'::uuid, 'cdb4c8de-e8ba-4612-8701-241b10eb8042'::uuid, '2026-02', 508.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ad8686e7-aee8-410c-b5bf-82b090b9c116'::uuid, 'eadcd43d-94b4-4a91-a565-02dde3a46310'::uuid, '2026-02', 1140.48, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('8a05e984-cee5-4afe-9333-36bd4de08c5e'::uuid, '3404182d-e4b1-4366-89fe-109aab61aba7'::uuid, '2026-02', 4060.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c2d0451c-cc7f-4469-8ea7-11d143f89fe6'::uuid, '9dcc6814-28e4-441d-9e92-da44a121535c'::uuid, '2026-02', 2380.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c77431b4-256d-406a-98cc-2cda9610a6e0'::uuid, '75d78964-5e1e-4856-9475-d62661b2215b'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c77431b4-256d-406a-98cc-2cda9610a6e0'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c77431b4-256d-406a-98cc-2cda9610a6e0'::uuid, '5a891672-43d7-46b2-9581-79260491814f'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c77431b4-256d-406a-98cc-2cda9610a6e0'::uuid, '9dcc6814-28e4-441d-9e92-da44a121535c'::uuid, '2026-02', 1200.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5602679b-b206-4633-b332-3d0bdebc639a'::uuid, '24cf60c6-bfb0-4b33-9a67-302ea1c78910'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5602679b-b206-4633-b332-3d0bdebc639a'::uuid, '6a305177-6f47-4ac0-85e7-e137619257bf'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5602679b-b206-4633-b332-3d0bdebc639a'::uuid, '35ca30ef-1db0-4b32-8970-f863e834a71a'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5602679b-b206-4633-b332-3d0bdebc639a'::uuid, '5c686592-4e2c-4865-9431-05581f02d7a2'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5602679b-b206-4633-b332-3d0bdebc639a'::uuid, '4ca7cd02-691c-4a64-b0ea-d5d20ede3941'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('6d77e580-d79d-4b3b-b922-d093a884218c'::uuid, 'daed2614-db01-4ca9-8926-67eb0069c301'::uuid, '2026-02', 2252.40, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d4fb45a9-ab07-4c74-b627-82897e7fa232'::uuid, '9c396be8-eba8-4f64-82af-acc6762b997c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d4fb45a9-ab07-4c74-b627-82897e7fa232'::uuid, '17331cc8-9aa7-4df5-a39b-a38ab32d3bee'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d4fb45a9-ab07-4c74-b627-82897e7fa232'::uuid, '6d1e7db3-1a98-4c20-aa96-1f4bde7ee901'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d4fb45a9-ab07-4c74-b627-82897e7fa232'::uuid, '66547848-64b1-4b3d-82aa-53101b319000'::uuid, '2026-02', 3150.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('df03ab18-173d-4268-86aa-a2e0452270cd'::uuid, '3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('df03ab18-173d-4268-86aa-a2e0452270cd'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('df03ab18-173d-4268-86aa-a2e0452270cd'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('df03ab18-173d-4268-86aa-a2e0452270cd'::uuid, '66807f9a-30dd-457e-9207-55ab5a10e0f9'::uuid, '2026-02', 5250.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('9734de36-f2f7-4e78-8e7a-52e7284af9d0'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 2600.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('69b104af-86b8-4b86-951b-7a7477ad8b2e'::uuid, '124417e6-78df-46d0-a70b-8e597c7006c6'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('69b104af-86b8-4b86-951b-7a7477ad8b2e'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('69b104af-86b8-4b86-951b-7a7477ad8b2e'::uuid, 'e52ab2e4-3351-42e5-91b0-721658014c5e'::uuid, '2026-02', 13500.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('cb4cd9a3-4ea8-4c08-b905-ec481f49b0da'::uuid, '1f148982-eb29-411e-8be5-fb89c1b14f8c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('cb4cd9a3-4ea8-4c08-b905-ec481f49b0da'::uuid, 'cb6d919e-2293-4555-9088-a502404df079'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('860143b0-5c0e-49a2-80bb-976a57c5c1c2'::uuid, '1f8f1790-40a3-49da-bc7f-53bcdaf32dd0'::uuid, '2026-02', 570.24, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('55d7dcb3-a0cd-473c-9523-0673952a884c'::uuid, '9f2d4706-1589-422c-9c85-d1f54af507a6'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('55d7dcb3-a0cd-473c-9523-0673952a884c'::uuid, '127d4f8f-5026-4839-ae7a-94f4a9587547'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('55d7dcb3-a0cd-473c-9523-0673952a884c'::uuid, '8a5282fd-7b46-40dc-bdb3-3a8a9023c109'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('55d7dcb3-a0cd-473c-9523-0673952a884c'::uuid, 'af990d28-a209-4907-9dcf-8477a87a77d5'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('55d7dcb3-a0cd-473c-9523-0673952a884c'::uuid, '66807f9a-30dd-457e-9207-55ab5a10e0f9'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('55d7dcb3-a0cd-473c-9523-0673952a884c'::uuid, 'f852e91d-aaea-4624-952d-f38c2f73a9b6'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('55d7dcb3-a0cd-473c-9523-0673952a884c'::uuid, '6bec2577-b724-44e3-9b67-a8ddc211d3da'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('55d7dcb3-a0cd-473c-9523-0673952a884c'::uuid, '69450eea-dd25-4f21-ada2-42d0bc0142ef'::uuid, '2026-02', 3200.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('56b3d8d4-6d4a-45f9-8c79-af55cc91e182'::uuid, 'be00c4ba-86dc-4752-a727-01dc65bf664d'::uuid, '2026-02', 2000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ebec3edc-0f6e-4f58-acb5-7d3ecc305a13'::uuid, '4beab894-ce34-4475-a5e0-6b7fce7387f6'::uuid, '2026-02', 9535.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('2af2a1a9-e1e9-4a8d-9ff4-c956065a2436'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 7638.16, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a5d0fc84-d5c4-4ab7-a838-eba105f9b9f4'::uuid, '1e7ffac2-e617-41fd-bad2-eae8077dc5fe'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('62590f5b-d06d-400a-b5c5-21c6b1571b8a'::uuid, '17606b42-4f1a-44ef-a09c-932e234a8ccf'::uuid, '2026-02', 620.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('86f2c3ea-4c76-438d-b37c-a974dfc08f78'::uuid, '404cbf03-f768-4029-9451-7d9303df9679'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('86f2c3ea-4c76-438d-b37c-a974dfc08f78'::uuid, '489dd2a6-de7d-46ca-b08b-c56f789b71cc'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('86f2c3ea-4c76-438d-b37c-a974dfc08f78'::uuid, '11c9b64b-e9c5-40b2-9e9f-9dc0fdc2f5db'::uuid, '2026-02', 2300.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('81f5dbd0-7e5e-4756-aeed-091db642e50c'::uuid, '1e7ffac2-e617-41fd-bad2-eae8077dc5fe'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a7074742-a413-4641-a1c3-29123b1430eb'::uuid, '1e7ffac2-e617-41fd-bad2-eae8077dc5fe'::uuid, '2026-02', 2500.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f5916daf-5c9f-427f-9fe7-07c698834b8e'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 4772.50, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('6918d3ff-77d0-4ce0-8e11-2612613b878d'::uuid, '7bcefc0d-03eb-44f2-9329-124e4a5ad8fe'::uuid, '2026-02', 14980.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('61ea2948-7eaf-4048-9236-8fa29f011f4d'::uuid, '6c462ca9-f819-45c3-bdd0-82353ea51d9c'::uuid, '2026-02', 16150.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('6f8b9301-0c30-4844-bb1f-77ccd84b40a6'::uuid, '02b16232-c617-4c05-b26e-7ec04a165278'::uuid, '2026-02', 2100.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a76fbf1f-edf7-43c6-826c-de43c9842244'::uuid, '030dddcf-8d69-4749-bd0d-e30a0bf5a009'::uuid, '2026-02', 8000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e52a40c5-a4ba-4a21-8ee8-349a8da29760'::uuid, 'be00c4ba-86dc-4752-a727-01dc65bf664d'::uuid, '2026-02', 6708.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('1092589d-ea85-4532-9edf-51e943276ab4'::uuid, '3404182d-e4b1-4366-89fe-109aab61aba7'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('1092589d-ea85-4532-9edf-51e943276ab4'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 3596.43, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c2cfbd14-cc3f-4825-9053-ea17cbf2e1bf'::uuid, '0f363f4a-0b1d-486f-86c7-61939a69ec13'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c2cfbd14-cc3f-4825-9053-ea17cbf2e1bf'::uuid, '8f2b2dd1-268e-477c-991d-dbebad7cb709'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c2cfbd14-cc3f-4825-9053-ea17cbf2e1bf'::uuid, 'b4a4e021-8e8b-4b6d-8ea7-5290d4bcdac5'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c2cfbd14-cc3f-4825-9053-ea17cbf2e1bf'::uuid, 'a5c4dc0d-fcfc-48c9-a3e8-99a50a7013cd'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c2cfbd14-cc3f-4825-9053-ea17cbf2e1bf'::uuid, 'f0092b86-a6be-4c67-9ac2-b8087af63008'::uuid, '2026-02', 1600.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('908b6fc7-f007-4258-a240-15482c89b8fa'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 6316.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5158f26f-4e3f-445e-8979-902d4369bb11'::uuid, '2f30cf19-9676-4a05-a2f5-3abbda0ae2e4'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5158f26f-4e3f-445e-8979-902d4369bb11'::uuid, 'b4a4e021-8e8b-4b6d-8ea7-5290d4bcdac5'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5158f26f-4e3f-445e-8979-902d4369bb11'::uuid, '0f363f4a-0b1d-486f-86c7-61939a69ec13'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5158f26f-4e3f-445e-8979-902d4369bb11'::uuid, 'f0092b86-a6be-4c67-9ac2-b8087af63008'::uuid, '2026-02', 39850.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('8dbd6ff7-6750-40a1-a34b-faa34f40840a'::uuid, '47bf28e5-972d-48ca-addb-56bf89eb406a'::uuid, '2026-02', 3780.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a15cf41a-8d97-41f5-bf6c-df4ce9810883'::uuid, '4bb28819-fee4-487d-8269-7508cdb01849'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a15cf41a-8d97-41f5-bf6c-df4ce9810883'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 1800.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('80ca9bcb-5033-4714-af71-1ceebdcc40b7'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('80ca9bcb-5033-4714-af71-1ceebdcc40b7'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 4810.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('0bb6882c-a583-4ffa-aeca-b21ae07324b1'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 2445.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('21686ce4-48d0-4d34-b7be-c8c20c1c79f9'::uuid, 'b713ae3e-aae6-4264-8a29-83642689d0f9'::uuid, '2026-02', 9271.15, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('7785bbbd-92f6-4653-8ec5-4c6f45b63dd4'::uuid, '02b16232-c617-4c05-b26e-7ec04a165278'::uuid, '2026-02', 1080.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('be5bd423-0ef2-4414-b1fa-6356369e0a32'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 4480.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3140bc17-6d5c-4c03-b284-abee86d89823'::uuid, 'ca6b8a69-a923-4d38-975c-4eb7fbbf2c7a'::uuid, '2026-02', 2980.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('dbb3a9d9-90e1-4daf-8752-42025dc45c59'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 5200.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('7442b8e9-c426-4f19-aa08-b63638a56425'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 19500.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('42847a10-edde-42c8-a44f-1f525f114131'::uuid, '47bf28e5-972d-48ca-addb-56bf89eb406a'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('42847a10-edde-42c8-a44f-1f525f114131'::uuid, '045fd18d-2103-413d-8c1d-a3ba59510253'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('35e94720-a485-444c-9af8-af9a089dc662'::uuid, 'd81a4bf9-0be7-49d6-9330-130cbedeaca6'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('35e94720-a485-444c-9af8-af9a089dc662'::uuid, '9f2d4706-1589-422c-9c85-d1f54af507a6'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('35e94720-a485-444c-9af8-af9a089dc662'::uuid, '127d4f8f-5026-4839-ae7a-94f4a9587547'::uuid, '2026-02', 2250.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('b1fa0861-7584-4a3a-ad45-d4afc8de9bf7'::uuid, '0663cef7-cdf5-4ec1-9916-8aba60fc0c20'::uuid, '2026-02', 7480.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ccd43d4b-c972-4a54-bdf5-8e22133cc519'::uuid, 'd29229cb-15ee-46a6-986f-129a96367659'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ce8a6789-d809-4476-ab5e-1f2911b56c7d'::uuid, 'c40743d3-a4b6-4061-ac12-c5b6a5e43a34'::uuid, '2026-02', 8269.60, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('515f9fed-7971-4ef3-bde0-aef6737f0b2e'::uuid, '66807f9a-30dd-457e-9207-55ab5a10e0f9'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('515f9fed-7971-4ef3-bde0-aef6737f0b2e'::uuid, '0f363f4a-0b1d-486f-86c7-61939a69ec13'::uuid, '2026-02', 22651.27, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('28d526da-91df-471f-927a-812938ff7cfe'::uuid, '66547848-64b1-4b3d-82aa-53101b319000'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('28d526da-91df-471f-927a-812938ff7cfe'::uuid, '6d1e7db3-1a98-4c20-aa96-1f4bde7ee901'::uuid, '2026-02', 2280.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('58c4a339-b09b-48d2-a588-5a11f0951cb8'::uuid, '17606b42-4f1a-44ef-a09c-932e234a8ccf'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('58c4a339-b09b-48d2-a588-5a11f0951cb8'::uuid, '72e3c253-8b52-4bd5-9b72-48b067286bb6'::uuid, '2026-02', 6580.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d5a80208-a9dc-4c7e-83b4-9a97728035cf'::uuid, '2518a12a-480e-49b7-a3f4-2fbdad3dce7b'::uuid, '2026-02', 1950.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('9eaafac1-a807-49cd-bcfe-c40281410c5e'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('36f32488-2f23-4c9a-9b84-463ea9bc2957'::uuid, '25541751-40c8-498f-9e22-b797c1714e8e'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('36f32488-2f23-4c9a-9b84-463ea9bc2957'::uuid, '8a5282fd-7b46-40dc-bdb3-3a8a9023c109'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3dc744d3-40a4-4fab-841e-505cd1869f6c'::uuid, '9f2d4706-1589-422c-9c85-d1f54af507a6'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3dc744d3-40a4-4fab-841e-505cd1869f6c'::uuid, '6bec2577-b724-44e3-9b67-a8ddc211d3da'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3dc744d3-40a4-4fab-841e-505cd1869f6c'::uuid, '66807f9a-30dd-457e-9207-55ab5a10e0f9'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3dc744d3-40a4-4fab-841e-505cd1869f6c'::uuid, '127d4f8f-5026-4839-ae7a-94f4a9587547'::uuid, '2026-02', 12100.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d67b4437-7850-4297-b78b-38b0e89ae8c8'::uuid, '94e38e26-60a0-4108-8332-5c7e02d83f50'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e059f8f7-977d-4d53-9207-ed3ff42a3d8d'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e059f8f7-977d-4d53-9207-ed3ff42a3d8d'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 730.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('579304fe-152a-47b0-9820-e7a15a48fe29'::uuid, '4c614b42-3f87-481f-9b22-8167a56c1c25'::uuid, '2026-02', 9000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('19e8785e-3afe-43cc-ac58-e642040995cf'::uuid, '4c614b42-3f87-481f-9b22-8167a56c1c25'::uuid, '2026-02', 29980.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('8a1f5b67-9750-4472-b35f-eb89d375a326'::uuid, '8fe43bf7-3261-4336-a4e9-a58b5ef3c366'::uuid, '2026-02', 8980.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('74770cd5-37b9-4763-817c-aea383761fa4'::uuid, '19aa0b12-e9c5-4a85-b462-a6b599f9e349'::uuid, '2026-02', 5892.55, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('80b44046-1689-481e-8e2b-79ef3e123d35'::uuid, '9c396be8-eba8-4f64-82af-acc6762b997c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('80b44046-1689-481e-8e2b-79ef3e123d35'::uuid, '66547848-64b1-4b3d-82aa-53101b319000'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('80b44046-1689-481e-8e2b-79ef3e123d35'::uuid, '6d1e7db3-1a98-4c20-aa96-1f4bde7ee901'::uuid, '2026-02', 1650.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('cefa8d1f-0e1f-4a7a-a809-b6cd1ff3c79b'::uuid, 'db9f68ca-be04-4765-bb45-4f2c49309c7a'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('eec8122e-e221-4f82-95a5-54084615c792'::uuid, '4c614b42-3f87-481f-9b22-8167a56c1c25'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('eec8122e-e221-4f82-95a5-54084615c792'::uuid, '1ce72d39-e901-4750-b758-f9e3b58d75ae'::uuid, '2026-02', 14100.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('359db675-fb60-4259-9557-c9c6883e2b9a'::uuid, '080a8741-1d8d-432f-9bf6-3e36b06700bc'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('359db675-fb60-4259-9557-c9c6883e2b9a'::uuid, '127d4f8f-5026-4839-ae7a-94f4a9587547'::uuid, '2026-02', 2250.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('02085979-1013-4011-ade9-edf69e2b3ea6'::uuid, '489dd2a6-de7d-46ca-b08b-c56f789b71cc'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('02085979-1013-4011-ade9-edf69e2b3ea6'::uuid, '404cbf03-f768-4029-9451-7d9303df9679'::uuid, '2026-02', 22800.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('818f017c-19b6-4111-be90-ae9d87dcde5f'::uuid, 'db769249-13d3-4d83-9fb5-93fcb39d5819'::uuid, '2026-02', 12780.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('1835b261-a51d-43cf-84ee-5b299858cfc9'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 6316.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('db9098b8-5c70-4627-a5b6-1f6cc9297d82'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('db9098b8-5c70-4627-a5b6-1f6cc9297d82'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 1768.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('1d9e86c4-3b6f-4be4-a80d-c54d6a4d1030'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('1d9e86c4-3b6f-4be4-a80d-c54d6a4d1030'::uuid, '3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, '2026-02', 650.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('555efb7d-394c-4887-9d7d-891618586cba'::uuid, '1e7ffac2-e617-41fd-bad2-eae8077dc5fe'::uuid, '2026-02', 5020.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f8580fc7-0d4a-4f9b-871e-ae156a97012d'::uuid, 'b26c91bf-43ed-4e98-80a6-288b83a110df'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f8580fc7-0d4a-4f9b-871e-ae156a97012d'::uuid, '02b16232-c617-4c05-b26e-7ec04a165278'::uuid, '2026-02', 2100.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('96218abb-c520-42ab-bd0f-b15f0430b379'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 15296.32, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a06e401e-d767-48a1-82d6-e722b56d1dc0'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 11590.47, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('998f28a7-e0b1-486a-8056-dab5b052f0d6'::uuid, 'd73faddc-610e-484e-8851-23d808738f83'::uuid, '2026-02', 9240.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('9dd08f9d-d14b-4233-846e-2e15770e49fe'::uuid, '8d828bde-3a22-461c-888d-d8612fdfb910'::uuid, '2026-02', 19600.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('37dd7f1f-0c3f-48ff-aa28-46b5e34778ce'::uuid, '9c396be8-eba8-4f64-82af-acc6762b997c'::uuid, '2026-02', 2627.80, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d35cf18e-eb45-43b9-97eb-be89e7b4a6ce'::uuid, '67de2622-d5e7-4c74-af02-27424750c07c'::uuid, '2026-02', 1480.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ecd4b7d7-2939-4cd6-b12d-ea5bf2912315'::uuid, '66547848-64b1-4b3d-82aa-53101b319000'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ecd4b7d7-2939-4cd6-b12d-ea5bf2912315'::uuid, '9c396be8-eba8-4f64-82af-acc6762b997c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ecd4b7d7-2939-4cd6-b12d-ea5bf2912315'::uuid, '6d1e7db3-1a98-4c20-aa96-1f4bde7ee901'::uuid, '2026-02', 4200.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3d747e9a-16a7-4d52-ad35-396f597e9010'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('46d6114c-99c7-4ebe-b390-87a2c19ba6ca'::uuid, '66547848-64b1-4b3d-82aa-53101b319000'::uuid, '2026-02', 15600.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('b0a31421-de11-4d01-8adb-7e4ce6525d04'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('63d1c2f3-387a-46e0-a9fe-2e40bfdd8ff4'::uuid, '6e0c2495-0bf8-4698-bef4-eab8562e22e7'::uuid, '2026-02', 3095.20, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('8b69e5b5-0e4f-46e6-b84b-9f6ebdd366fb'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('8b69e5b5-0e4f-46e6-b84b-9f6ebdd366fb'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 1950.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a37f29db-58ac-4add-b595-d6296534c9de'::uuid, 'cdb4c8de-e8ba-4612-8701-241b10eb8042'::uuid, '2026-02', 2134.24, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('8a756442-c97c-47e9-92bb-6ab5e3d128a5'::uuid, '404cbf03-f768-4029-9451-7d9303df9679'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('8a756442-c97c-47e9-92bb-6ab5e3d128a5'::uuid, '489dd2a6-de7d-46ca-b08b-c56f789b71cc'::uuid, '2026-02', 5000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('4848b036-add0-4b45-a486-544d3e1eb1ec'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 2600.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c081d69e-8a3e-4e2a-836b-eb404a203d8b'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c081d69e-8a3e-4e2a-836b-eb404a203d8b'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 3042.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5ba8156a-b115-48ce-b813-9130e4524ade'::uuid, '15472bd9-a182-45ce-983e-c1579da653ea'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5ba8156a-b115-48ce-b813-9130e4524ade'::uuid, '124417e6-78df-46d0-a70b-8e597c7006c6'::uuid, '2026-02', 8700.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('02061ff0-4ccd-4486-bd25-05f87f83e0aa'::uuid, 'f2da6473-d7db-4cef-bdfc-de7867836797'::uuid, '2026-02', 2811.93, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a6d012c5-f24a-479c-8244-d7e0bbaf537b'::uuid, 'ca6b8a69-a923-4d38-975c-4eb7fbbf2c7a'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3f1583a7-c3b5-425b-9b5a-f9a40c59354a'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 10374.67, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('b829dd71-69ca-4a59-b67f-7d522ae79f0a'::uuid, '4c892f40-4cfb-436f-8221-8320dd465b09'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d9378788-3a6a-4bba-aa65-540095843ddf'::uuid, 'be00c4ba-86dc-4752-a727-01dc65bf664d'::uuid, '2026-02', 23348.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d2da699f-18c6-4921-907a-79dde680bf8a'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d2da699f-18c6-4921-907a-79dde680bf8a'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d2da699f-18c6-4921-907a-79dde680bf8a'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d2da699f-18c6-4921-907a-79dde680bf8a'::uuid, '9dcc6814-28e4-441d-9e92-da44a121535c'::uuid, '2026-02', 280.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f1ae332b-2e39-4e1e-935a-47fe4535e362'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f1ae332b-2e39-4e1e-935a-47fe4535e362'::uuid, '3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, '2026-02', -842.56, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('671af4d5-d664-40af-a513-031508aedc02'::uuid, '404cbf03-f768-4029-9451-7d9303df9679'::uuid, '2026-02', 4500.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('140b6a22-309f-4fd6-8559-3410bc671110'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 16900.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('b78341b5-2143-435e-be61-89342a877eab'::uuid, '67de2622-d5e7-4c74-af02-27424750c07c'::uuid, '2026-02', 2980.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('cc0c3a6a-fd26-4153-8ccc-9305a5b32f2c'::uuid, '29f3be09-dca5-42bb-b658-2ce133b3fb96'::uuid, '2026-02', 1036.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('bcef18bb-846c-4f74-a7a1-a70ebfd2d70f'::uuid, '4beab894-ce34-4475-a5e0-6b7fce7387f6'::uuid, '2026-02', 7700.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3810c382-7859-4af3-af3e-14552abf653d'::uuid, '9c396be8-eba8-4f64-82af-acc6762b997c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3810c382-7859-4af3-af3e-14552abf653d'::uuid, '17331cc8-9aa7-4df5-a39b-a38ab32d3bee'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3810c382-7859-4af3-af3e-14552abf653d'::uuid, '6d1e7db3-1a98-4c20-aa96-1f4bde7ee901'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3810c382-7859-4af3-af3e-14552abf653d'::uuid, '66547848-64b1-4b3d-82aa-53101b319000'::uuid, '2026-02', 3500.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f7218a0a-9abe-4c36-8ad0-4c9cb09a0d26'::uuid, '6d1e7db3-1a98-4c20-aa96-1f4bde7ee901'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f7218a0a-9abe-4c36-8ad0-4c9cb09a0d26'::uuid, '66547848-64b1-4b3d-82aa-53101b319000'::uuid, '2026-02', 24000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e78a5973-1978-4986-8a72-b6ff36c1e9c4'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 6316.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3ae43f80-bd75-4f9c-b31c-005f53cddc21'::uuid, '77c23072-16a4-48bd-a1fc-308cdeace495'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3ae43f80-bd75-4f9c-b31c-005f53cddc21'::uuid, '97ed68fd-e2a3-447b-b5cc-3b66cf29626f'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3ae43f80-bd75-4f9c-b31c-005f53cddc21'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3ae43f80-bd75-4f9c-b31c-005f53cddc21'::uuid, '3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3ae43f80-bd75-4f9c-b31c-005f53cddc21'::uuid, '2e9b5517-eeb3-47d2-afe5-619ac0ef9a20'::uuid, '2026-02', 4830.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d8b744f9-eb0a-468a-a1dc-3d6c188bdf84'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d8b744f9-eb0a-468a-a1dc-3d6c188bdf84'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d8b744f9-eb0a-468a-a1dc-3d6c188bdf84'::uuid, '3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, '2026-02', 650.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('18a9a79c-a2cb-48be-a167-78b520188f80'::uuid, '3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('18a9a79c-a2cb-48be-a167-78b520188f80'::uuid, '8d828bde-3a22-461c-888d-d8612fdfb910'::uuid, '2026-02', 2800.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('00925fd3-adc4-4fc4-9899-1579e2641308'::uuid, '4c614b42-3f87-481f-9b22-8167a56c1c25'::uuid, '2026-02', 8980.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d3eed807-516b-4c4e-9550-02325dce6c61'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 300.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('1405df85-540a-483c-ba4b-bfeb1cf6f745'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 14764.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a6d0213e-d247-46ea-86b8-075e7d4ecf9f'::uuid, '02b16232-c617-4c05-b26e-7ec04a165278'::uuid, '2026-02', 505.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('69301a57-b3d1-48dd-894d-2384fbeaebc8'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 195.21, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3f6f3ae4-7e6d-4b9f-909b-74798402fe72'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 244.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('1ba889e7-c336-4361-ac9a-08c592e22497'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 6058.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('91d36b05-8b3c-4f28-9db5-5fce13a33c64'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('91d36b05-8b3c-4f28-9db5-5fce13a33c64'::uuid, '3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, '2026-02', 2200.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ab5d4627-75d2-48b3-a2de-357666a86d28'::uuid, 'c590b3f7-87d4-4c06-a6ae-14fa232b9ecc'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ab5d4627-75d2-48b3-a2de-357666a86d28'::uuid, '9960c157-9313-410d-a2cf-471eb688a51f'::uuid, '2026-02', 12000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('24e00bfd-f9fa-4bc7-b4c9-78d3b69a8da2'::uuid, '1e7ffac2-e617-41fd-bad2-eae8077dc5fe'::uuid, '2026-02', 10060.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('837e7228-1808-4b91-98af-20b64a075897'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('837e7228-1808-4b91-98af-20b64a075897'::uuid, '3404182d-e4b1-4366-89fe-109aab61aba7'::uuid, '2026-02', 1780.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('bec16e98-43d7-4453-b4fe-ac01a39d04e8'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 1000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('44e636d9-c75b-419b-9eb6-7b43c7779ea0'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 1828.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a787b2b9-21d5-4e37-8686-e4fe97c2671e'::uuid, '9dcc6814-28e4-441d-9e92-da44a121535c'::uuid, '2026-02', 3280.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('fe861299-f85d-41ad-a5e4-caf99290b32f'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 1930.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ff912966-093b-4bc7-8b58-17f6aae83870'::uuid, '8d828bde-3a22-461c-888d-d8612fdfb910'::uuid, '2026-02', 4200.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('dece4ee4-5e40-4a50-8a08-f77154b91122'::uuid, 'f6b9f9b7-14cb-4ced-aebe-8d076e4a775f'::uuid, '2026-02', 3885.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('cb914365-32f0-461c-a274-52889e6c1bca'::uuid, 'be00c4ba-86dc-4752-a727-01dc65bf664d'::uuid, '2026-02', 2364.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('4934ce04-2651-4fdb-a15f-b613d0b17e93'::uuid, '8d828bde-3a22-461c-888d-d8612fdfb910'::uuid, '2026-02', 8400.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('cd5acf88-f67b-4e93-965a-b72e0f2d3395'::uuid, '8d828bde-3a22-461c-888d-d8612fdfb910'::uuid, '2026-02', 22400.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('89216d62-2478-4a43-acb8-e6f956275827'::uuid, 'd25690c8-54c1-4bdb-b0da-00bb6f7353d1'::uuid, '2026-02', 6900.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('61ba679a-7db1-4fbf-8f40-c708be2aeac0'::uuid, '5a891672-43d7-46b2-9581-79260491814f'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('61ba679a-7db1-4fbf-8f40-c708be2aeac0'::uuid, '59715aba-3102-44d5-b7c2-b5323fefb7c3'::uuid, '2026-02', 2696.25, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ae5db091-1a6d-4843-be81-5a32dc2afa11'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 6100.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('06a1c7b2-bea6-4203-9a9c-e1cd422efbdc'::uuid, 'c40743d3-a4b6-4061-ac12-c5b6a5e43a34'::uuid, '2026-02', 1214.40, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e48983f7-dd06-488f-9bbf-5afbc5ed97b5'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e48983f7-dd06-488f-9bbf-5afbc5ed97b5'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 1000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e0f16321-07a8-445d-8959-a469b6e81f83'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e0f16321-07a8-445d-8959-a469b6e81f83'::uuid, '3404182d-e4b1-4366-89fe-109aab61aba7'::uuid, '2026-02', 3730.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('054b8ab6-0d53-431d-b8bd-b025a0960ab3'::uuid, 'dc235b47-5ef4-48e7-ad0b-1664b3bfa44b'::uuid, '2026-02', 12000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('b4bb74b2-5186-4c95-a76b-d6d391bd51a2'::uuid, '1e7ffac2-e617-41fd-bad2-eae8077dc5fe'::uuid, '2026-02', 2500.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('03862e2f-2604-4ce5-8b49-b1cee207f6d3'::uuid, '3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('03862e2f-2604-4ce5-8b49-b1cee207f6d3'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 2510.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('354156ff-48c7-417e-abcc-81f292f3dcbe'::uuid, '15df1ff2-5ade-4c74-b856-7a81443370db'::uuid, '2026-02', 12000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('75cb39ec-b030-4630-8efd-4277ff638630'::uuid, '1f148982-eb29-411e-8be5-fb89c1b14f8c'::uuid, '2026-02', 13560.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d5321fa2-1011-473a-a3be-7f1870a2c6a9'::uuid, '4fcdbed0-9539-4bb7-a29f-5812abcf04f3'::uuid, '2026-02', 16500.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('175d0777-c28f-4df7-a61a-62a3102d30b1'::uuid, '3404182d-e4b1-4366-89fe-109aab61aba7'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('175d0777-c28f-4df7-a61a-62a3102d30b1'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 1080.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('40fd4b91-7a2b-4170-93dc-c5ac6bc2194c'::uuid, '8d828bde-3a22-461c-888d-d8612fdfb910'::uuid, '2026-02', 11200.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c36c44bd-0ad1-47a3-8ea8-c71086b3a606'::uuid, 'f7dca287-f378-4eaa-9a3d-e90b5f102a43'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c36c44bd-0ad1-47a3-8ea8-c71086b3a606'::uuid, '020eb4cf-2d63-4ab0-9eea-617ac0cb345c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c36c44bd-0ad1-47a3-8ea8-c71086b3a606'::uuid, '1f8f1790-40a3-49da-bc7f-53bcdaf32dd0'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c36c44bd-0ad1-47a3-8ea8-c71086b3a606'::uuid, '53f83a95-0f93-462f-896e-d605d07859d0'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c36c44bd-0ad1-47a3-8ea8-c71086b3a606'::uuid, 'eadcd43d-94b4-4a91-a565-02dde3a46310'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c36c44bd-0ad1-47a3-8ea8-c71086b3a606'::uuid, 'edec0dd8-4cb2-4b27-b8a0-f55b6e7d154a'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c36c44bd-0ad1-47a3-8ea8-c71086b3a606'::uuid, 'cdb4c8de-e8ba-4612-8701-241b10eb8042'::uuid, '2026-02', 528.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('9d7c0998-ab94-4d0e-a496-77a1c10ee941'::uuid, 'f350d63f-712a-457d-8272-27c87ac0351c'::uuid, '2026-02', 1980.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('1d02222d-bd2c-44f7-84b6-3f3da1c13d14'::uuid, '1f8f1790-40a3-49da-bc7f-53bcdaf32dd0'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('1d02222d-bd2c-44f7-84b6-3f3da1c13d14'::uuid, 'edec0dd8-4cb2-4b27-b8a0-f55b6e7d154a'::uuid, '2026-02', 352.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e99b32dd-b140-440f-ac17-af215ea9572e'::uuid, 'eb895306-d199-42c0-936d-49503131bfb0'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e99b32dd-b140-440f-ac17-af215ea9572e'::uuid, 'bc883f46-6d9e-44ad-94a4-3c25fe2b4bdd'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e99b32dd-b140-440f-ac17-af215ea9572e'::uuid, '2518a12a-480e-49b7-a3f4-2fbdad3dce7b'::uuid, '2026-02', 7370.80, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('2bb97a45-b96e-435a-8220-10002507d0dd'::uuid, 'b26c91bf-43ed-4e98-80a6-288b83a110df'::uuid, '2026-02', 1080.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('42c8ac39-62e4-490b-99f6-3814a22e484c'::uuid, '53f83a95-0f93-462f-896e-d605d07859d0'::uuid, '2026-02', 2196.48, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('69d33d91-3fc1-4a49-9afe-ef673b595304'::uuid, '2e9b5517-eeb3-47d2-afe5-619ac0ef9a20'::uuid, '2026-02', 6750.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f74f8852-8de3-4e00-be02-bbf14530626b'::uuid, 'c590b3f7-87d4-4c06-a6ae-14fa232b9ecc'::uuid, '2026-02', 12000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d60a0de0-dc3d-41c8-8e76-0d89483fa402'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 1000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a53b0df8-dea4-4c8c-a4a1-baa2ba9aa009'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 3148.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a40cac7c-cea4-40fa-890b-bc40e66897a7'::uuid, '127d4f8f-5026-4839-ae7a-94f4a9587547'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a40cac7c-cea4-40fa-890b-bc40e66897a7'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a40cac7c-cea4-40fa-890b-bc40e66897a7'::uuid, '3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a40cac7c-cea4-40fa-890b-bc40e66897a7'::uuid, '66807f9a-30dd-457e-9207-55ab5a10e0f9'::uuid, '2026-02', 1500.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e8d9dece-a712-4b34-bdf4-70fa4098a371'::uuid, '3404182d-e4b1-4366-89fe-109aab61aba7'::uuid, '2026-02', 2080.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('db59c4e2-92b9-4f71-8ac2-4275a23131be'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 12652.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('6019d544-f21d-4723-b2a9-09f7418f25f7'::uuid, 'f4264e3e-d79a-42eb-baf1-d6a2e3f0b442'::uuid, '2026-02', 5200.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('56bb91f8-a778-4b02-a18c-c037a64358fa'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 1255.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('8f8b917e-7cb1-4d29-a656-66c203c9f6d2'::uuid, '72e3c253-8b52-4bd5-9b72-48b067286bb6'::uuid, '2026-02', 14742.61, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e0fa7dab-3616-40ad-b794-797779e83adc'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e0fa7dab-3616-40ad-b794-797779e83adc'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 800.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('80ec17b6-f382-4fbc-aeab-685018f05f41'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 5760.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('2edad9c3-926a-4efe-9a70-715915868965'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('2edad9c3-926a-4efe-9a70-715915868965'::uuid, '9dcc6814-28e4-441d-9e92-da44a121535c'::uuid, '2026-02', 2973.75, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('4a58dc03-e0ac-4de1-aa16-7dd356486f1d'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 3880.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('240e6154-b1f1-456b-ad8f-76b83d2a475b'::uuid, '4beab894-ce34-4475-a5e0-6b7fce7387f6'::uuid, '2026-02', 9800.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('cd5e2d0c-0fc0-42ad-b6f4-7dc86009d3b4'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 1828.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('9c63bcba-cb48-4fd3-a8f4-0d5479e89b26'::uuid, 'cb6d919e-2293-4555-9088-a502404df079'::uuid, '2026-02', 56000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('7d41a7e0-3d71-4b65-9a74-84959fbc89fc'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 5080.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('2db24298-fba0-4c28-a338-2ea74ad9450d'::uuid, '406cbb47-ab51-445e-a5d2-e6a36f6634ef'::uuid, '2026-02', 6541.24, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e4044f32-7939-4f22-9f05-7f1b053209ba'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 580.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('25394e49-e246-4b6b-93f0-7ef689ffc0a7'::uuid, '8d828bde-3a22-461c-888d-d8612fdfb910'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('25394e49-e246-4b6b-93f0-7ef689ffc0a7'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 650.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3def32e0-3f7e-455e-9ad9-eb18127e7c54'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 3250.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('7d6fe736-511f-43b7-bc18-23f9163a3179'::uuid, 'be00c4ba-86dc-4752-a727-01dc65bf664d'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('7d6fe736-511f-43b7-bc18-23f9163a3179'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 1200.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('6f35d53a-4909-46f0-8904-87951efcc9ba'::uuid, '85f5634b-85c3-4559-8dc1-cba7bc79e631'::uuid, '2026-02', 2800.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f9f707f6-d0e6-4c82-9b37-3ba58159ff0c'::uuid, '6eeb2a2f-e3af-4ba8-834d-f747c86ac9a9'::uuid, '2026-02', 5914.72, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('49bdc115-dddf-4314-8162-5d265ecef570'::uuid, 'f7dca287-f378-4eaa-9a3d-e90b5f102a43'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('49bdc115-dddf-4314-8162-5d265ecef570'::uuid, 'edec0dd8-4cb2-4b27-b8a0-f55b6e7d154a'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('49bdc115-dddf-4314-8162-5d265ecef570'::uuid, '1f8f1790-40a3-49da-bc7f-53bcdaf32dd0'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('49bdc115-dddf-4314-8162-5d265ecef570'::uuid, '020eb4cf-2d63-4ab0-9eea-617ac0cb345c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('347211f9-3a64-404a-a8b8-8edb5690bdf1'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 2380.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('cd32c91b-bb0e-4efe-93d9-99fa8e73376f'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 8340.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('02a16a8d-422c-4473-bf98-f9d5fc459305'::uuid, 'b713ae3e-aae6-4264-8a29-83642689d0f9'::uuid, '2026-02', 6580.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('2a647f5f-5455-4b9a-8029-5e9423599f17'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('85c49073-8247-4855-a560-59ff45cefb9a'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 2600.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('4738d0a2-b4df-4bf1-9b92-9fb4e5eee38c'::uuid, '9dcc6814-28e4-441d-9e92-da44a121535c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('4738d0a2-b4df-4bf1-9b92-9fb4e5eee38c'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 1180.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('6941c4d3-a191-4dfe-8629-f8d22f5ffd5d'::uuid, '1e7ffac2-e617-41fd-bad2-eae8077dc5fe'::uuid, '2026-02', 4180.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('595feab9-631c-4f5e-9526-7254c508b729'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 4732.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f8da8630-14e9-4909-b2ca-824fcbb2e46e'::uuid, '3404182d-e4b1-4366-89fe-109aab61aba7'::uuid, '2026-02', 780.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('32398b7c-5726-4198-95f7-84d6bacef967'::uuid, '030dddcf-8d69-4749-bd0d-e30a0bf5a009'::uuid, '2026-02', 9272.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('34b1595b-ad26-43a1-af3d-886727236d63'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 2232.40, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('444e05dd-a934-4700-b0b4-3a7762593431'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 3180.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('874564ce-b477-438a-a928-adf5cad560d4'::uuid, '4c614b42-3f87-481f-9b22-8167a56c1c25'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('874564ce-b477-438a-a928-adf5cad560d4'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 1036.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('4fb847e6-ad15-483c-ba5d-e1ccb2979f07'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 7150.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('6576503b-8c87-4c67-a0e2-0d5311ca6b42'::uuid, '0f363f4a-0b1d-486f-86c7-61939a69ec13'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('6576503b-8c87-4c67-a0e2-0d5311ca6b42'::uuid, 'a5c4dc0d-fcfc-48c9-a3e8-99a50a7013cd'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('6576503b-8c87-4c67-a0e2-0d5311ca6b42'::uuid, '8f2b2dd1-268e-477c-991d-dbebad7cb709'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('6576503b-8c87-4c67-a0e2-0d5311ca6b42'::uuid, 'b4a4e021-8e8b-4b6d-8ea7-5290d4bcdac5'::uuid, '2026-02', 2800.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('210873a8-b47d-4ff7-84cd-3d7640b27c6b'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 4342.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e6d81665-14d6-48b9-8939-92207164b491'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 3148.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a3fa7508-9c8f-45a1-9e14-0e36bc5d306c'::uuid, '1e7ffac2-e617-41fd-bad2-eae8077dc5fe'::uuid, '2026-02', 18460.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('91da98fd-0dc3-44e0-949a-9f1aa318837e'::uuid, '02b16232-c617-4c05-b26e-7ec04a165278'::uuid, '2026-02', 1050.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('97acb1dc-dbbf-452e-9a5c-0fc8e6781618'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 830.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e01f56ec-b7ab-4051-bde4-c13931cdb940'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 650.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('4d24fd39-285d-49b6-ae08-4549b32a91ba'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 12476.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('43630398-447e-4691-adb9-af0838a5125c'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 19190.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3f35e3b8-0a45-4196-830d-fd3ece40f1c8'::uuid, '94e38e26-60a0-4108-8332-5c7e02d83f50'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3f35e3b8-0a45-4196-830d-fd3ece40f1c8'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3f35e3b8-0a45-4196-830d-fd3ece40f1c8'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 750.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c905ae79-f13b-4e6e-ae54-bbfe4a258f69'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 430.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5417266e-f604-4650-ae3e-1fbfc326ee54'::uuid, '4beab894-ce34-4475-a5e0-6b7fce7387f6'::uuid, '2026-02', 4760.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('0a7611ce-396e-48df-a458-ba1d07cc0756'::uuid, 'f72ee1c4-a349-4039-bcee-0e47b8ebab8e'::uuid, '2026-02', 650.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('af659cd8-a09b-4f7d-b382-d436adde6fbe'::uuid, '4fc2ee21-316c-4137-aa7f-397d056f99c9'::uuid, '2026-02', 1580.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d744caa6-2d1f-4852-8c3e-9d7362e17687'::uuid, '1e7ffac2-e617-41fd-bad2-eae8077dc5fe'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d744caa6-2d1f-4852-8c3e-9d7362e17687'::uuid, 'f350d63f-712a-457d-8272-27c87ac0351c'::uuid, '2026-02', 3980.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a3dc021c-9767-45af-a4a0-6f878be9a9b5'::uuid, '2cc4f825-95f3-4c2a-a906-a26bd7539a5f'::uuid, '2026-02', 3000.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('503aa578-9b42-4794-9c72-8f2a2b054b94'::uuid, 'f6b9f9b7-14cb-4ced-aebe-8d076e4a775f'::uuid, '2026-02', 3500.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f9756ad2-caaa-4e98-bcec-6810fcf17c14'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 8149.93, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c3dc05e9-36f3-4882-96f2-d4511bbf803d'::uuid, '4bb28819-fee4-487d-8269-7508cdb01849'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('0c5be8f7-38e2-4d5e-9f84-98606f39124d'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 718.75, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('27928a2a-ff4b-4940-9f9f-89445145be80'::uuid, 'be00c4ba-86dc-4752-a727-01dc65bf664d'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('27928a2a-ff4b-4940-9f9f-89445145be80'::uuid, '4c614b42-3f87-481f-9b22-8167a56c1c25'::uuid, '2026-02', 20699.21, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3f92dd38-2f80-4c80-9235-ae481b6e04e1'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 1780.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('f98b5595-75b3-4ebe-a4c3-7b6581f0d6fe'::uuid, 'be00c4ba-86dc-4752-a727-01dc65bf664d'::uuid, '2026-02', 4708.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('060b53c6-9b81-4289-b776-31ba600de41e'::uuid, 'f2da6473-d7db-4cef-bdfc-de7867836797'::uuid, '2026-02', 5600.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('5b833d3b-0a3c-4336-9313-e6da52dbe6dd'::uuid, '72e3c253-8b52-4bd5-9b72-48b067286bb6'::uuid, '2026-02', 4930.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('2b09bad4-b468-403a-ac80-8f365beaac7f'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('2b09bad4-b468-403a-ac80-8f365beaac7f'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 480.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3895b526-194e-4ca0-a8c4-d86ad65e4cd4'::uuid, '8d828bde-3a22-461c-888d-d8612fdfb910'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('3895b526-194e-4ca0-a8c4-d86ad65e4cd4'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 8034.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('e123e94e-bddd-4142-a723-265f8ff5c910'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 280.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('482f5207-f731-4c44-ae11-05edc85593d2'::uuid, '21e3591c-c081-40ba-af15-8403a2848176'::uuid, '2026-02', 5250.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('0c50a225-8451-43c8-b8d5-d1f6d5301859'::uuid, '52b14bfd-b2b3-4b2c-babd-d7bdf69871ab'::uuid, '2026-02', 2380.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('c2b644ed-7d1b-47b5-bbe7-3efd208a02fe'::uuid, '5c18756e-e633-484a-ad30-632d81ddcc41'::uuid, '2026-02', 4780.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('afd53e87-444a-4d22-86cf-db2e526531b6'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 2020.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('bcc3c2b8-74e3-4f06-8962-5c748b76c9f4'::uuid, '75d78964-5e1e-4856-9475-d62661b2215b'::uuid, '2026-02', 5380.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('02b01d94-2a3f-47ae-8c53-a10adeabdedc'::uuid, '463a87fe-eda9-4250-9ae3-4d14a51223b6'::uuid, '2026-02', 4204.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d780e8d1-bd22-4595-88dd-e836ce3b9103'::uuid, '3de8a240-d30a-4744-a30d-15391d32cf0c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d780e8d1-bd22-4595-88dd-e836ce3b9103'::uuid, '8acc0781-662c-4199-b59d-5509acbe1e31'::uuid, '2026-02', 4797.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('da58d167-1d36-4cf6-a788-4f3b8d4484a0'::uuid, '1f8f1790-40a3-49da-bc7f-53bcdaf32dd0'::uuid, '2026-02', 508.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('64c5d8d1-c7fe-4a8c-a459-201d73f1e393'::uuid, '3404182d-e4b1-4366-89fe-109aab61aba7'::uuid, '2026-02', 9180.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ef40c4fb-54c9-4695-ad3f-c6f233317755'::uuid, 'ccd06afa-87a9-45c8-8d83-832304f1e64b'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ef40c4fb-54c9-4695-ad3f-c6f233317755'::uuid, '5761bcc8-c8a5-41bd-8417-f0d9e9787a1d'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('ef40c4fb-54c9-4695-ad3f-c6f233317755'::uuid, 'dd82e46f-5c1c-4b60-a506-e1f9865e56e5'::uuid, '2026-02', 2040.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('97f1801a-5095-4709-874c-b41fc35eb065'::uuid, 'f350d63f-712a-457d-8272-27c87ac0351c'::uuid, '2026-02', 3980.00, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('b85f75af-6da1-44df-8ee1-fb662e5e06c1'::uuid, '729f4582-745e-4770-ac22-4e40d82d76a7'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('d1b63acf-f5e8-4bb7-8789-8e6c92f170a2'::uuid, '8c4b9ed2-9c36-4f3f-bc1c-296abdadf618'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('8a6cf9ea-5439-474d-99d0-a488d7cdb09e'::uuid, '3df173e1-1ac4-45ff-943b-3fe9dfb173c0'::uuid, '2026-02', 7999.92, 'ELEGIVEL');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a2bdd159-28f2-4719-811c-1b3fd78e2fcf'::uuid, '3df173e1-1ac4-45ff-943b-3fe9dfb173c0'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('994c29e8-caae-408e-b53a-7cd11b276991'::uuid, '72e3c253-8b52-4bd5-9b72-48b067286bb6'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('994c29e8-caae-408e-b53a-7cd11b276991'::uuid, '47bf28e5-972d-48ca-addb-56bf89eb406a'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('994c29e8-caae-408e-b53a-7cd11b276991'::uuid, '67de2622-d5e7-4c74-af02-27424750c07c'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('994c29e8-caae-408e-b53a-7cd11b276991'::uuid, 'f4264e3e-d79a-42eb-baf1-d6a2e3f0b442'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('994c29e8-caae-408e-b53a-7cd11b276991'::uuid, '0663cef7-cdf5-4ec1-9916-8aba60fc0c20'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('994c29e8-caae-408e-b53a-7cd11b276991'::uuid, '045fd18d-2103-413d-8c1d-a3ba59510253'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('994c29e8-caae-408e-b53a-7cd11b276991'::uuid, '4fc2ee21-316c-4137-aa7f-397d056f99c9'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('55c94a6e-4076-4db5-8d51-08dfabe9e45d'::uuid, '729f4582-745e-4770-ac22-4e40d82d76a7'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('aebaf6bd-e59e-42d7-8279-71d28d3bce3e'::uuid, '8c4b9ed2-9c36-4f3f-bc1c-296abdadf618'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('a6495af4-a6d1-47b6-892b-e9531a3b1d04'::uuid, '023db8d5-c25c-43cc-ab75-ab1b9cbbd371'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('988bc3a4-d4f3-486c-b0d1-dd19b17c8b23'::uuid, 'f350d63f-712a-457d-8272-27c87ac0351c'::uuid, '2026-02', -20.00, 'SALDO_NEGATIVO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('4ee3ef18-211b-41f5-8b2e-5821803fbe85'::uuid, '3df173e1-1ac4-45ff-943b-3fe9dfb173c0'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('cbbd7d71-15b1-4fd4-bd71-ff19bc90174e'::uuid, '8a5282fd-7b46-40dc-bdb3-3a8a9023c109'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('cbbd7d71-15b1-4fd4-bd71-ff19bc90174e'::uuid, '97c3137d-1cf8-4a83-ad7b-18d6619f050f'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('196a9222-a373-4fc9-b676-eb0951b2c4f7'::uuid, '023db8d5-c25c-43cc-ab75-ab1b9cbbd371'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('079144d0-f81a-4d7e-9a8d-3c28958a2aec'::uuid, '729f4582-745e-4770-ac22-4e40d82d76a7'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');
INSERT INTO registro_pp (prestador_id, contrato_id, mes_competencia, saldo_pp, status_saldo)
VALUES ('7fa67b00-ef02-474b-b780-5e79a364854a'::uuid, '023db8d5-c25c-43cc-ab75-ab1b9cbbd371'::uuid, '2026-02', 0.00, 'SEM_MOVIMENTO');

COMMIT;
