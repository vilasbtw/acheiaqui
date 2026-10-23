# Importar todos os models aqui garante que o SQLAlchemy conheça as relações entre eles.
from app.models.campus import Campus  # noqa: F401
from app.models.categoria import Categoria  # noqa: F401
from app.models.item import Item  # noqa: F401
from app.models.devolucao import Devolucao  # noqa: F401
from app.models.cae_membro import CaeMembro  # noqa: F401
