from fastapi import status
from fastapi.testclient import TestClient

CHAVE = "21260912345678000123550010001234561234567890"
HEADERS = {"X-Internal-API-Key": "test-internal-key"}
WORKER_HEADERS = {"X-Worker-API-Key": "test-worker-key"}

RESUMO_LEITOR = {
    "operacao_id": "2b7e3ef6-0e41-4bf7-8f73-8d0bb0aa4a11",
    "total_notas": 4,
    "tentadas": 5,
    "cadastradas": 1,
    "duplicadas": 1,
    "ignoradas": 1,
    "erros": 1,
    "valor_total": "100.00",
    "valor_cadastradas": "40.00",
    "valor_duplicadas": "20.00",
    "valor_ignoradas": "30.00",
    "valor_erros": "10.00",
    "tempo_total_segundos": "12.50",
    "tempo_notas_segundos": "10.00",
}


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


def test_resumo_do_leitor_e_idempotente(client: TestClient) -> None:
    response = client.post(
        "/integracao/leitor/resumos",
        headers=HEADERS,
        json=RESUMO_LEITOR,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["valor_erros"] == "10.00"

    replay = client.post(
        "/integracao/leitor/resumos",
        headers=HEADERS,
        json=RESUMO_LEITOR,
    )
    assert replay.status_code == status.HTTP_200_OK
    assert replay.json()["id"] == response.json()["id"]

    conflito = {**RESUMO_LEITOR, "valor_erros": "11.00"}
    response_conflitante = client.post(
        "/integracao/leitor/resumos",
        headers=HEADERS,
        json=conflito,
    )
    assert response_conflitante.status_code == status.HTTP_409_CONFLICT
    assert response_conflitante.json()["code"] == (
        "RESUMO_OPERACAO_LEITOR_CONFLITANTE"
    )
