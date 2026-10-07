from concurrent.futures import ThreadPoolExecutor

from fastapi import status
from fastapi.testclient import TestClient

CHAVE = "21260912345678000123550010001234561234567890"
CHAVE_2 = "21260912345678000123550010001234561234567891"
HEADERS = {"X-Worker-API-Key": "test-worker-key"}
INTERNAL_HEADERS = {"X-Internal-API-Key": "test-internal-key"}


def importar_nota(client: TestClient, chave: str) -> None:
    response = client.post(
        "/integracao/notas/importar-txt",
        headers=INTERNAL_HEADERS,
        json={
            "nome_arquivo": "notas.txt",
            "total_linhas": 1,
            "total_invalidas": 0,
            "total_duplicadas_txt": 0,
            "chaves": [chave],
        },
    )
    assert response.status_code == status.HTTP_200_OK


def test_worker_rejeita_sem_api_key(client: TestClient) -> None:
    response = client.post("/worker/notas/proxima")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_worker_rejeita_api_key_invalida(client: TestClient) -> None:
    response = client.post(
        "/worker/notas/proxima",
        headers={"X-Worker-API-Key": "errada"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_worker_claim_retorna_204_sem_trabalho(client: TestClient) -> None:
    response = client.post("/worker/notas/proxima", headers=HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_worker_claim_consulta_e_registra_resultado(client: TestClient) -> None:
    importar_nota(client, CHAVE)

    claim = client.post("/worker/notas/proxima", headers=HEADERS)
    execucao_id = claim.json()["execucao_id"]
    execucao = client.get(f"/worker/execucoes/{execucao_id}", headers=HEADERS)
    resultado = client.post(
        f"/worker/execucoes/{execucao_id}/resultado",
        headers=HEADERS,
        json={
            "status": "SUCESSO",
            "mensagem": "Nota cadastrada com sucesso",
            "valor": "89.90",
            "data_emissao": "2026-08-30",
            "tempo_segundos": "8.74",
        },
    )
    repetido = client.post(
        f"/worker/execucoes/{execucao_id}/resultado",
        headers=HEADERS,
        json={
            "status": "SUCESSO",
            "mensagem": "Nota cadastrada com sucesso",
            "valor": "89.90",
            "data_emissao": "2026-08-30",
            "tempo_segundos": "8.74",
        },
    )
    conflito = client.post(
        f"/worker/execucoes/{execucao_id}/resultado",
        headers=HEADERS,
        json={"status": "ERRO", "mensagem": "erro tardio"},
    )

    assert claim.status_code == status.HTTP_200_OK
    assert claim.json()["tentativa"] == 1
    assert execucao.status_code == status.HTTP_200_OK
    assert execucao.json()["status"] == "EM_EXECUCAO"
    assert resultado.status_code == status.HTTP_200_OK
    assert resultado.json()["status"] == "SUCESSO"
    assert repetido.status_code == status.HTTP_200_OK
    assert conflito.status_code == status.HTTP_409_CONFLICT


def test_worker_claim_concorrente_entrega_notas_diferentes(client: TestClient) -> None:
    for chave in [CHAVE, CHAVE_2]:
        importar_nota(client, chave)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda _: client.post("/worker/notas/proxima", headers=HEADERS),
                range(2),
            ),
        )

    assert [response.status_code for response in responses] == [
        status.HTTP_200_OK,
        status.HTTP_200_OK,
    ]
    assert len({response.json()["nota_id"] for response in responses}) == 2


def test_worker_claim_concorrente_com_uma_nota_retorna_204(client: TestClient) -> None:
    importar_nota(client, CHAVE)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda _: client.post("/worker/notas/proxima", headers=HEADERS),
                range(2),
            ),
        )

    assert sorted(response.status_code for response in responses) == [
        status.HTTP_200_OK,
        status.HTTP_204_NO_CONTENT,
    ]
