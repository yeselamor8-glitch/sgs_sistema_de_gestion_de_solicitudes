from sgs.motores.motor_auth import hashear_password, verificar_password


def test_password_correcta_verifica_ok():
    hash_guardado = hashear_password("ClaveSegura123")
    assert verificar_password("ClaveSegura123", hash_guardado) is True


def test_password_incorrecta_no_verifica():
    hash_guardado = hashear_password("ClaveSegura123")
    assert verificar_password("otra_clave", hash_guardado) is False


def test_nunca_se_guarda_en_texto_plano():
    hash_guardado = hashear_password("ClaveSegura123")
    assert "ClaveSegura123" not in hash_guardado


def test_dos_hashes_de_la_misma_password_son_distintos_por_el_salt():
    hash1 = hashear_password("ClaveSegura123")
    hash2 = hashear_password("ClaveSegura123")
    assert hash1 != hash2
    assert verificar_password("ClaveSegura123", hash1)
    assert verificar_password("ClaveSegura123", hash2)


def test_hash_corrupto_no_lanza_error_solo_no_verifica():
    assert verificar_password("cualquier_cosa", "esto-no-es-un-hash-valido") is False