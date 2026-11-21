"""
Aviso por e-mail para quem perdeu (Etapa 7, D28): só com consentimento e só depois que a CAE confirmou.

Roda em segundo plano (BackgroundTasks do FastAPI): a CAE recebe a resposta na hora e o e-mail sai logo depois.
A tarefa abre a PRÓPRIA sessão do banco, porque a da requisição já foi fechada quando ela roda.
O resultado fica em perdidos.aviso_enviado_em / aviso_erro, e a CAE vê no painel (e pode reenviar).
Limitação conhecida: se o Render reiniciar entre a resposta e o envio, o e-mail não sai; o painel mostra "pendente".
"""
from sqlalchemy.orm import joinedload, sessionmaker

from app.models.perdido import Perdido
from app.services.email import enviar_email
from app.tempo import agora_local

ASSUNTO = "Achei Aqui: seu item pode estar na CAE"


def montar_aviso(perdido: Perdido) -> str:
    campus = perdido.campus
    retirada = campus.info_retirada or "Procure a CAE do seu campus."
    return (
        "Olá!\n\n"
        f"A CAE do campus {campus.nome} encontrou um item que parece ser o que você perdeu.\n\n"
        f"Você registrou: {perdido.descricao}\n"
        f"Item encontrado: {perdido.item.descricao}\n\n"
        f"Como retirar: {retirada}\n"
        "Leve um documento com foto. A CAE confere com você se o item é mesmo seu antes de entregar.\n\n"
        "Você recebeu este e-mail porque pediu um aviso ao registrar o item perdido no Achei Aqui.\n"
        "Se não foi você, pode ignorar esta mensagem.\n"
    )


def enviar_aviso(fabrica_de_sessao: sessionmaker, perdido_id: int) -> None:
    with fabrica_de_sessao() as sessao:
        perdido = (
            sessao.query(Perdido)
            .options(joinedload(Perdido.campus), joinedload(Perdido.item))
            .filter(Perdido.id == perdido_id)
            .one_or_none()
        )
        # Confere de novo: entre o clique e o envio, a CAE pode ter desfeito a confirmação.
        if perdido is None or perdido.status != "encontrado" or not perdido.aviso_consentido or not perdido.email_aviso:
            return
        erro = enviar_email(perdido.email_aviso, ASSUNTO, montar_aviso(perdido))
        if erro is None:
            perdido.aviso_enviado_em = agora_local()
        perdido.aviso_erro = erro
        sessao.commit()
