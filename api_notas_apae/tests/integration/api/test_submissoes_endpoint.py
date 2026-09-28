from fastapi import status
from fastapi.testclient import TestClient

CHAVE = "21260912345678000123550010001234561234567890"


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_post_submissoes_cria_e_depois_detecta_duplicada(
    client: TestClient,
) -> None:
    payload = {
        "telefone": "5598999999999",
        "origem": "MANUAL",
        "chave": CHAVE,
    }

    first = client.post("/submissoes", json=payload)
    second = client.post("/submissoes", json=payload)

    assert first.status_code == status.HTTP_201_CREATED
    assert first.json()["status"] == "PENDENTE"
    assert first.json()["duplicada"] is False
    assert second.status_code == status.HTTP_201_CREATED
    assert second.json()["status"] == "DUPLICADA"
    assert second.json()["duplicada"] is True
    assert second.json()["nota_id"] == first.json()["nota_id"]
    assert second.json()["submissao_id"] != first.json()["submissao_id"]


def test_get_nota_por_chave(client: TestClient) -> None:
    client.post(
        "/submissoes",
        json={"telefone": "5598999999999", "origem": "MANUAL", "chave": CHAVE},
    )

    response = client.get(f"/notas/chave/{CHAVE}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["chave"] == CHAVE
    assert response.json()["status"] == "PENDENTE"


def test_listar_notas_paginado(client: TestClient) -> None:
    client.post(
        "/submissoes",
        json={"telefone": "5598999999999", "origem": "MANUAL", "chave": CHAVE},
    )

    response = client.get("/notas?page=1&size=20")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["chave"] == CHAVE


def test_historico_submissoes_e_pessoa(client: TestClient) -> None:
    first = client.post(
        "/submissoes",
        json={"telefone": "5598999999999", "origem": "MANUAL", "chave": CHAVE},
    ).json()
    client.post(
        "/submissoes",
        json={"telefone": "5598999999999", "origem": "MANUAL", "chave": CHAVE},
    )

    submissoes = client.get(f"/notas/{first['nota_id']}/submissoes")
    pessoa = client.get("/pessoas/telefone/5598999999999")
    notas_da_pessoa = client.get(f"/pessoas/{pessoa.json()['id']}/notas")

    assert submissoes.status_code == status.HTTP_200_OK
    assert len(submissoes.json()) == 2
    assert pessoa.status_code == status.HTTP_200_OK
    assert notas_da_pessoa.status_code == status.HTTP_200_OK
    assert len(notas_da_pessoa.json()) == 1


def test_execucao_resultado_e_reprocessamento(client: TestClient) -> None:
    nota_id = client.post(
        "/submissoes",
        json={"telefone": "5598999999999", "origem": "MANUAL", "chave": CHAVE},
    ).json()["nota_id"]

    execucao = client.post(f"/notas/{nota_id}/execucoes")
    resultado = client.post(
        f"/notas/{nota_id}/resultado-cadastro",
        json={
            "execucao_id": execucao.json()["id"],
            "status": "ERRO",
            "mensagem": "falha externa",
            "tempo_segundos": "1.2",
        },
    )
    reprocessada = client.post(f"/notas/{nota_id}/reprocessar")
    historico = client.get(f"/notas/{nota_id}/execucoes")

    assert execucao.status_code == status.HTTP_201_CREATED
    assert execucao.json()["tentativa"] == 1
    assert resultado.status_code == status.HTTP_200_OK
    assert resultado.json()["status"] == "ERRO"
    assert reprocessada.status_code == status.HTTP_200_OK
    assert reprocessada.json()["status"] == "PENDENTE"
    assert len(historico.json()) == 1


def test_post_submissoes_rejeita_chave_invalida(client: TestClient) -> None:
    response = client.post(
        "/submissoes",
        json={"telefone": "5598999999999", "origem": "MANUAL", "chave": "123"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "CHAVE_INVALIDA"
