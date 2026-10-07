from fastapi import status
from fastapi.testclient import TestClient

CHAVE = "21260912345678000123550010001234561234567890"
HEADERS = {"X-Internal-API-Key": "test-internal-key"}
WORKER_HEADERS = {"X-Worker-API-Key": "test-worker-key"}


def test_importacao_txt_cria_nota_na_api(client: TestClient) -> None:
    response = client.post(
        "/integracao/notas/importar-txt",
        headers=HEADERS,
        json={
            "nome_arquivo": "notas.txt",
            "total_linhas": 2,
            "total_invalidas": 1,
            "total_duplicadas_txt": 0,
            "chaves": [CHAVE],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total_inseridas"] == 1

    notas = client.get("/notas", headers=WORKER_HEADERS)
    assert notas.status_code == status.HTTP_200_OK
    assert notas.json()["items"][0]["chave"] == CHAVE
    assert notas.json()["items"][0]["status"] == "PENDENTE"


def test_importacao_txt_reativa_nota_com_erro(client: TestClient) -> None:
    client.post(
        "/integracao/notas/importar-txt",
        headers=HEADERS,
        json={
            "nome_arquivo": "notas.txt",
            "total_linhas": 1,
            "total_invalidas": 0,
            "total_duplicadas_txt": 0,
            "chaves": [CHAVE],
        },
    )
    claim = client.post(
        "/worker/notas/proxima",
        headers=WORKER_HEADERS,
    )
    execution_id = claim.json()["execucao_id"]
    result = client.post(
        f"/worker/execucoes/{execution_id}/resultado",
        headers=WORKER_HEADERS,
        json={"status": "ERRO", "mensagem": "falha de teste"},
    )
    assert result.status_code == status.HTTP_200_OK

    response = client.post(
        "/integracao/notas/importar-txt",
        headers=HEADERS,
        json={
            "nome_arquivo": "notas.txt",
            "total_linhas": 1,
            "total_invalidas": 0,
            "total_duplicadas_txt": 0,
            "chaves": [CHAVE],
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total_reativadas"] == 1
