"""
Teste de integracao com dados sinteticos (sem arquivos reais).
Verifica todo o pipeline: PP -> Extrato -> Conciliacao
"""

import sys, os, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import openpyxl
from openpyxl import Workbook


def criar_pp_sintetico(path):
    """Cria um arquivo PP XLSX sintetico com 2 prestadores."""
    wb = Workbook()
    ws = wb.active
    
    # Linhas 1-3: cabecalho global
    ws.append(["SPM - Sistema de Pagamentos Medicos"])
    ws.append(["Periodo: 01/04/2026 a 09/04/2026"])
    ws.append(["Gerado em: 12/04/2026"])
    ws.append([])  # linha vazia
    
    # Bloco 1: Prestador 1 - CPF
    ws.append(["JOAO DA SILVA  -  123456/SP"])
    ws.append(["Transacao: PIX  Tipo de Documento: CPF  Chave Pix: 12345678900  Documento: 12345678900  Razao social: "])
    ws.append(["Data", "Local", "Tipo", "Duracao (h)", "Valor", "Total", "Total Pago", "Saldo"])

    import datetime
    ws.append([datetime.date(2026, 4, 1), "HOSPITAL ALPHA", "PLANTAO", 12, 1500.0, 1500.0, 0.0, 1234.56])
    ws.append([datetime.date(2026, 4, 3), "HOSPITAL ALPHA", "PLANTAO", 12, 1500.0, 3000.0, 0.0, 1234.56])
    ws.append(["Total", None, None, None, None, None, None, 1234.56])
    ws.append([])  # separador
    
    # Bloco 2: Prestador 2 - CNPJ
    ws.append(["MARIA SANTOS  -  78901/RJ"])
    ws.append(["Transacao: PIX  Tipo de Documento: CNPJ  Chave Pix: 12345678000190  Documento: 12345678000190  Razao social: CLINICA MARIA LTDA"])
    ws.append(["Data", "Local", "Tipo", "Duracao (h)", "Valor", "Total", "Total Pago", "Saldo"])
    ws.append([datetime.date(2026, 4, 2), "CLINICA BETA", "PLANTAO", 6, 800.0, 800.0, 0.0, 567.89])
    ws.append(["Total", None, None, None, None, None, None, 567.89])
    ws.append([])
    
    wb.save(path)
    return path


def criar_ofx_sintetico(path):
    """Cria um arquivo OFX sintetico."""
    content = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS><STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<DTSERVER>20260412000000</DTSERVER><LANGUAGE>POR</LANGUAGE>
</SONRS></SIGNONMSGSRSV1>
<BANKMSGSRSV1><STMTTRNRS><TRNUID>1</TRNUID>
<STMTRS><CURDEF>BRL</CURDEF>
<BANKACCTFROM><BANKID>0237</BANKID><ACCTID>12345-6</ACCTID><ACCTTYPE>CHECKING</ACCTTYPE></BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20260401120000</DTPOSTED>
<TRNAMT>-1234,56</TRNAMT>
<FITID>TXN001</FITID>
<MEMO>TRANSFERENCIA PIX REM: JOAO DA SILVA   01/04</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20260402110000</DTPOSTED>
<TRNAMT>-567,89</TRNAMT>
<FITID>TXN002</FITID>
<MEMO>TRANSFERENCIA PIX REM: CLINICA MARIA LTDA   02/04</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20260401080000</DTPOSTED>
<TRNAMT>5000,00</TRNAMT>
<FITID>TXN003</FITID>
<MEMO>TED-TRANSF ELET RECEBIDO HOSPITAL ABC</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20260401090000</DTPOSTED>
<TRNAMT>-45,67</TRNAMT>
<FITID>TXN004</FITID>
<MEMO>TARIFA BANCARIA MANUTENCAO CONTA</MEMO>
</STMTTRN>
</BANKTRANLIST>
</STMTRS></STMTTRNRS></BANKMSGSRSV1>
</OFX>"""
    Path(path).write_text(content, encoding="latin-1")
    return path


def test_integracao_completa():
    """Testa o pipeline completo com dados sinteticos."""
    print("=== TESTE DE INTEGRACAO COMPLETA ===")
    
    from pega_plantao import parse_relatorio
    from extrato_bradesco import parse_extrato
    from conciliacao_spm import conciliar
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pp_path = criar_pp_sintetico(tmpdir + "/pp_teste.xlsx")
        ofx_path = criar_ofx_sintetico(tmpdir + "/extrato_teste.ofx")
        
        # Parse PP
        pp_data = parse_relatorio(pp_path)
        print("PP: {} registros".format(len(pp_data)))
        assert len(pp_data) == 2, "Esperado 2 registros PP, obtido {}".format(len(pp_data))
        assert pp_data[0]["nome_prestador"] == "JOAO DA SILVA"
        assert pp_data[0]["contrato"] == "HOSPITAL ALPHA"
        assert abs(pp_data[0]["saldo"] - 1234.56) < 0.01
        assert pp_data[0]["tipo_doc"] == "CPF"
        print("  OK: PP parseado corretamente")
        
        # Parse Extrato
        extrato_data = parse_extrato(ofx_path)
        print("Extrato: {} transacoes".format(len(extrato_data)))
        assert len(extrato_data) == 4
        pix_saidas = [t for t in extrato_data if t["tipo"] == "PIX_SAIDA"]
        assert len(pix_saidas) == 2, "Esperado 2 PIX_SAIDA, obtido {}".format(len(pix_saidas))
        assert pix_saidas[0]["titular_pix"] == "JOAO DA SILVA"
        print("  OK: Extrato OFX parseado corretamente")
        
        # Conciliacao
        resultado = conciliar(pp_data, extrato_data)
        resumo = resultado["resumo"]
        print("Resumo:", resumo)
        
        # JOAO DA SILVA deve ter MATCH_AUTOMATICO (PIX 1234.56 == saldo 1234.56)
        reg_joao = next(r for r in resultado["registros"] if "JOAO" in r["nome_prestador"])
        print("Joao status: {}".format(reg_joao["status"]))
        assert reg_joao["status"] == "MATCH_AUTOMATICO", (
            "Esperado MATCH_AUTOMATICO, obtido {}".format(reg_joao["status"]))
        
        # MARIA SANTOS/CLINICA MARIA deve ter match por PJ
        reg_maria = next(r for r in resultado["registros"] if "MARIA" in r["nome_prestador"])
        print("Maria status: {}".format(reg_maria["status"]))
        assert reg_maria["status"] in ("MATCH_AUTOMATICO", "FRACIONADO", "MANUAL_PENDENTE")
        
        print("  OK: Conciliacao executada")
    
    print("\nTODOS OS TESTES PASSARAM!")


if __name__ == '__main__':
    test_integracao_completa()
