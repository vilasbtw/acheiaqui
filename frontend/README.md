Frontend - Achei Aqui

Este é o módulo frontend do portal Achei Aqui. Ele fornece a interface visual onde os usuários podem registrar e buscar itens achados e perdidos, além de um painel administrativo exclusivo para a CAE.

Tecnologias Utilizadas

HTML5 & CSS3: Estruturação e estilização das páginas, garantindo um design responsivo.

JavaScript (Vanilla): Lógica de interface, consumo da API REST e controle de estado no navegador.

Estrutura de Diretórios

/: Arquivos HTML públicos principais, como a página inicial (index.html) e a página de registro de itens (registrar.html).

/cae/: Área restrita para a Comissão de Assistência Estudantil, contendo o login (login.html) e o painel de administração (painel.html) onde os alertas do agente de IA são exibidos.

/css/: Arquivos de folha de estilo (style.css).

/js/: Scripts modulares divididos por responsabilidade:

api.js: Gerenciamento das requisições HTTP para o backend.

auth.js e login.js: Lógica de autenticação de usuários da CAE.

buscar.js e registrar.js: Funcionalidades da área pública do portal.

painel.js: Lógica do painel administrativo, incluindo o consumo das sugestões de match da IA.

Como Executar

O frontend não requer um build complexo. Basta servir a pasta raiz usando um servidor HTTP simples.

Navegue até a pasta frontend.

Execute o servidor embutido do Python: python -m http.server 5500



Acesse http://localhost:5500 no seu navegador.