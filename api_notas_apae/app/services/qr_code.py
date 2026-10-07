import logging
import os
import re

import cv2
import numpy as np

try:
    import pytesseract
except ImportError:  # pragma: no cover - a dependência é instalada em produção
    pytesseract = None

from app.services.validar_chave import validar_chave_acesso

MAX_IMAGE_BYTES = 10 * 1024 * 1024
logger = logging.getLogger(__name__)


def _regiao_acima_do_qr(imagem: np.ndarray) -> np.ndarray:
    """Retorna a área onde a chave costuma ser impressa, acima do QR Code."""
    altura, largura = imagem.shape[:2]
    detector = cv2.QRCodeDetector()

    for versao in (imagem, cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)):
        try:
            detectado, pontos = detector.detect(versao)
        except cv2.error:
            continue

        if detectado and pontos is not None:
            menor_y = max(0, int(np.min(pontos[:, :, 1])))
            if menor_y > 0:
                return imagem[:menor_y, :]

    # Quando o QR está presente, mas não pode ser localizado, ainda prioriza
    # a faixa superior, onde a chave da nota normalmente é impressa.
    return imagem[: max(1, int(altura * 0.45)), : largura]


def _candidatos_ocr(texto: str) -> list[str]:
    """Converte texto OCR em candidatos de 44 dígitos, tolerando separadores."""
    candidatos: list[str] = []
    for trecho in re.findall(r"[0-9][0-9\s./-]{42,}[0-9]", texto):
        somente_digitos = re.sub(r"\D", "", trecho)
        for inicio in range(max(1, len(somente_digitos) - 43)):
            candidato = somente_digitos[inicio : inicio + 44]
            if len(candidato) == 44 and validar_chave_acesso(candidato):
                if candidato not in candidatos:
                    candidatos.append(candidato)
    return candidatos


def ler_chave_ocr(imagem_bytes: bytes) -> list[str]:
    """Extrai uma chave fiscal impressa acima do QR quando o QR não bastou."""
    if pytesseract is None:
        logger.warning("OCR indisponível: instale pytesseract e o Tesseract OCR")
        return []

    comando_tesseract = os.getenv("TESSERACT_CMD")
    if comando_tesseract:
        pytesseract.pytesseract.tesseract_cmd = comando_tesseract

    array = np.frombuffer(imagem_bytes, dtype=np.uint8)
    try:
        imagem = cv2.imdecode(array, cv2.IMREAD_COLOR)
    except cv2.error as error:
        raise ValueError("Não foi possível decodificar a imagem") from error

    if imagem is None:
        raise ValueError("Não foi possível decodificar a imagem")

    regiao = _regiao_acima_do_qr(imagem)
    cinza = cv2.cvtColor(regiao, cv2.COLOR_BGR2GRAY)
    ampliada = cv2.resize(
        cinza,
        None,
        fx=3,
        fy=3,
        interpolation=cv2.INTER_CUBIC,
    )
    variantes = [
        ampliada,
        cv2.threshold(ampliada, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        cv2.adaptiveThreshold(
            ampliada,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            5,
        ),
    ]

    for variante in variantes:
        try:
            texto = pytesseract.image_to_string(
                variante,
                config="--psm 6 -c tessedit_char_whitelist=0123456789",
            )
        except (OSError, RuntimeError) as error:
            logger.warning("Falha ao executar OCR: %s", type(error).__name__)
            return []
        chaves = _candidatos_ocr(texto)
        if chaves:
            logger.info("Chave fiscal extraída por OCR")
            return chaves

    return []


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
                        logger.info("QR Code lido pelo OpenCV")
                        resultados.append(texto)

        except cv2.error:
            pass

        try:
            texto, _, _ = detector.detectAndDecode(versao)

            if texto and texto not in resultados:
                logger.info("QR Code lido pelo OpenCV")
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
