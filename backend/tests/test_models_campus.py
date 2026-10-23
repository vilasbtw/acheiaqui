"""Os models novos do multi-campus (Campus, CaeMembro e Item.campus_id) funcionam juntos."""
import uuid

from app.models.cae_membro import CaeMembro
from app.models.campus import Campus
from app.models.item import Item
from app.tempo import agora_local


def test_campus_membro_e_item_se_relacionam(sessao_teste):
    campus = Campus(sigla="tst", nome="Teste", cidade="Cidade de teste")
    sessao_teste.add(campus)
    sessao_teste.flush()
    assert campus.ativo is True
    assert campus.info_retirada == ""

    membro = CaeMembro(user_id=uuid.uuid4(), campus_id=campus.id)
    item = Item(descricao="Garrafa azul", local_encontrado="Cantina", encontrado_em=agora_local(), campus_id=campus.id)
    sessao_teste.add_all([membro, item])
    sessao_teste.flush()

    assert membro.id is not None
    assert item.campus_id == campus.id
    sessao_teste.rollback()  # não deixa nada para trás (no PostgreSQL o campus de teste não pode ficar)
