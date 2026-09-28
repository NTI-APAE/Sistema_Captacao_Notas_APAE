import logging

import cv2
import numpy as np

MAX_IMAGE_BYTES = 10 * 1024 * 1024
logger = logging.getLogger(__name__)


def ler_qr_code(imagem_bytes: bytes) -> list[str]:
    """
    Tenta ler QR Codes aplicando diferentes tratamentos
    à imagem, sem salvar o arquivo em disco.
    """
    if not imagem_bytes or len(imagem_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("Imagem vazia ou acima do limite permitido")

    array = np.frombuffer(imagem_bytes, dtype=np.uint8)
    try:
        imagem = cv2.imdecode(array, cv2.IMREAD_COLOR)
    except cv2.error as error:
        raise ValueError("Não foi possível decodificar a imagem") from error

    if imagem is None:
        raise ValueError("Não foi possível decodificar a imagem")

    detector = cv2.QRCodeDetector()
    resultados = []

    def tentar_decodificar(versao, descricao):
        logger.debug("Tentativa de leitura QR: %s", descricao)

        try:
            sucesso, textos, _, _ = detector.detectAndDecodeMulti(versao)

            if sucesso:
                for texto in textos:
                    if texto and texto not in resultados:
                        resultados.append(texto)

        except cv2.error:
            pass

        try:
            texto, _, _ = detector.detectAndDecode(versao)

            if texto and texto not in resultados:
                resultados.append(texto)

        except cv2.error:
            pass

    # 1. Imagem original
    tentar_decodificar(imagem, "original")

    if resultados:
        return resultados

    # 2. Escala de cinza
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)

    tentar_decodificar(cinza, "escala de cinza")

    if resultados:
        return resultados

    # 3. Ampliar a imagem
    ampliada = cv2.resize(
        cinza,
        None,
        fx=3,
        fy=3,
        interpolation=cv2.INTER_CUBIC,
    )

    tentar_decodificar(ampliada, "ampliada 3x")

    if resultados:
        return resultados

    # 4. Melhorar o contraste
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    contraste = clahe.apply(ampliada)

    tentar_decodificar(contraste, "contraste melhorado")

    if resultados:
        return resultados

    # 5. Binarização adaptativa
    binarizada = cv2.adaptiveThreshold(
        contraste,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        5,
    )

    tentar_decodificar(binarizada, "binarização adaptativa")

    return resultados
