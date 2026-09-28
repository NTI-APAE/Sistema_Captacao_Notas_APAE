import cv2
import numpy as np
import pytest


@pytest.fixture
def chave_valida():
    prefix = "2126091234567800012355001000123456123456789"
    soma = sum(int(n) * (2 + i % 8) for i, n in enumerate(reversed(prefix)))
    resto = soma % 11
    return prefix + str(0 if resto < 2 else 11 - resto)


@pytest.fixture
def imagem_qr(chave_valida):
    qr = cv2.QRCodeEncoder_create().encode(chave_valida)
    qr = cv2.copyMakeBorder(qr, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
    qr = cv2.resize(qr, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST)
    return cv2.imencode(".png", qr)[1].tobytes()


@pytest.fixture
def imagem_sem_qr():
    return cv2.imencode(".png", np.full((100, 100, 3), 255, dtype=np.uint8))[
        1
    ].tobytes()
