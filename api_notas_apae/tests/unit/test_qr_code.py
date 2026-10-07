from unittest.mock import Mock

import cv2
import numpy as np
import pytest

from app.services import qr_code
from app.services.validar_chave import extrair_chave_acesso, validar_chave_acesso


def test_leitura_real(imagem_qr, chave_valida):
    assert chave_valida in qr_code.ler_qr_code(imagem_qr)


def test_imagem_sem_qr(imagem_sem_qr):
    assert qr_code.ler_qr_code(imagem_sem_qr) == []


@pytest.mark.parametrize("content", [b"", b"nao e imagem"])
def test_imagem_invalida(content):
    with pytest.raises(ValueError):
        qr_code.ler_qr_code(content)


def test_limite_bytes():
    with pytest.raises(ValueError):
        qr_code.ler_qr_code(b"0" * (qr_code.MAX_IMAGE_BYTES + 1))


def test_erro_opencv_e_imagem_invalida(monkeypatch):
    monkeypatch.setattr(
        qr_code.cv2, "imdecode", Mock(side_effect=qr_code.cv2.error("bad"))
    )
    with pytest.raises(ValueError):
        qr_code.ler_qr_code(b"imagem corrompida")


def test_extracao_e_digito(chave_valida):
    for content in [
        chave_valida,
        f"{chave_valida}|2|1",
        f"https://exemplo.test/?chNFe={chave_valida}",
        f"https://exemplo.test/?p={chave_valida}%7C2%7C1",
    ]:
        assert extrair_chave_acesso(content) == chave_valida
    invalida = chave_valida[:-1] + str((int(chave_valida[-1]) + 1) % 10)
    assert not validar_chave_acesso(invalida)
    assert extrair_chave_acesso(invalida) is None
    assert not validar_chave_acesso("1" * 43)
    assert not validar_chave_acesso("١" * 44)


def test_todas_as_etapas_preservadas(monkeypatch, imagem_sem_qr, chave_valida):
    detector = Mock()
    detector.detectAndDecodeMulti.return_value = (False, (), None, None)
    detector.detectAndDecode.side_effect = [("", None, None)] * 4 + [
        (chave_valida, None, None)
    ]
    monkeypatch.setattr(qr_code.cv2, "QRCodeDetector", lambda: detector)
    assert qr_code.ler_qr_code(imagem_sem_qr) == [chave_valida]
    shapes = [call.args[0].shape for call in detector.detectAndDecode.call_args_list]
    assert shapes == [(100, 100, 3), (100, 100), (300, 300), (300, 300), (300, 300)]


def test_ocr_extrai_chave_formatada_na_faixa_superior(
    monkeypatch, imagem_sem_qr, chave_valida
):
    texto = " ".join(chave_valida[index : index + 4] for index in range(0, 44, 4))
    ocr = Mock()
    ocr.image_to_string.return_value = texto
    monkeypatch.setattr(qr_code, "pytesseract", ocr)

    assert qr_code.ler_chave_ocr(imagem_sem_qr) == [chave_valida]
    imagem_ocr = ocr.image_to_string.call_args.args[0]
    assert imagem_ocr.shape == (135, 300)


def test_ocr_ignora_chave_com_digito_invalido(monkeypatch, imagem_sem_qr, chave_valida):
    invalida = chave_valida[:-1] + str((int(chave_valida[-1]) + 1) % 10)
    ocr = Mock()
    ocr.image_to_string.return_value = invalida
    monkeypatch.setattr(qr_code, "pytesseract", ocr)

    assert qr_code.ler_chave_ocr(imagem_sem_qr) == []


def test_ocr_prioriza_regiao_acima_do_qr(monkeypatch, imagem_qr, chave_valida):
    ocr = Mock()
    ocr.image_to_string.return_value = chave_valida
    monkeypatch.setattr(qr_code, "pytesseract", ocr)

    assert qr_code.ler_chave_ocr(imagem_qr) == [chave_valida]
    imagem_ocr = ocr.image_to_string.call_args.args[0]
    imagem_original = cv2.imdecode(
        np.frombuffer(imagem_qr, dtype=np.uint8), cv2.IMREAD_COLOR
    )
    assert imagem_ocr.shape[0] < imagem_original.shape[0] * 3
