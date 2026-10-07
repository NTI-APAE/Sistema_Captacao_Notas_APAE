from fastapi import status
from fastapi.testclient import TestClient

CHAVE = "21260912345678000123550010001234561234567890"
INTERNAL_HEADERS = {"X-Internal-API-Key": "test-internal-key"}
WORKER_HEADERS = {"X-Worker-API-Key": "test-worker-key"}


def importar_nota(client: TestClient) -> None:
    response = client.post(
        "/integracao/notas/importar-txt",
        headers=INTERNAL_HEADERS,
        json={
            "nome_arquivo": "notas.txt",
            "total_linhas": 1,
            "total_invalidas": 0,
            "total_duplicadas_txt": 0,
            "chaves": [CHAVE],
        },
    )
    assert response.status_code == status.HTTP_200_OK


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_listar_notas_rejeita_sem_chave_do_worker(client: TestClient) -> None:
    response = client.get("/notas")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_consultar_nota_rejeita_sem_chave_do_worker(client: TestClient) -> None:
    response = client.get("/notas/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_listar_notas_paginado(client: TestClient) -> None:
    importar_nota(client)

    response = client.get("/notas?page=1&size=20", headers=WORKER_HEADERS)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["chave"] == CHAVE


def test_consultar_nota_por_id(client: TestClient) -> None:
    importar_nota(client)
    lista = client.get("/notas?page=1&size=20", headers=WORKER_HEADERS)
    nota_id = lista.json()["items"][0]["id"]

    response = client.get(f"/notas/{nota_id}", headers=WORKER_HEADERS)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["chave"] == CHAVE
