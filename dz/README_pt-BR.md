***Essa tradução se tornou possível graças a LadyApollo!***

# DZ

Um homebrew que permite extrair title keys, instalar jogos, atualizações e DLCs.


## Screenshots
![tile view](ss.jpg)
![install options](install.jpg)


## Instalação

 - Crie o diretório `/switch/dz/` no cartão SD do seu switch.
 - Copie o arquivo `dz.nro` para `/switch/dz/dz.nro`.
 - Obtenha ou gere um arquivo `keys.txt` coloque-o na pasta `/switch/dz/keys.txt`. `keys.txt` é um arquivo de texto contendo chaves encriptadas do Switch. Se você planeja gerar essas chaves, poderá encontras as instruções aqui:  https://gbatemp.net/threads/how-to-get-switch-keys-for-hactool-xci-decrypting.506978/ ou usar o applicativo [`kezplez-nx`](https://github.com/shchmue/kezplez-nx)
 - Copie o arquivo `locations.conf` para `/switch/dz/locations.conf`. Você deve editar esse arquivo, este é apenas um exemplo. Esse arquivo aponta para os diversos locais hospedando o conteúdo desejado para instalação, sendo local ou por rede. Você pode ver exemplos de como adicionar diversos [protocolos suportados](#supported-protocols) lendo o arquivo `locations.conf.example`s.


## Supported Protocols
Edite o arquivo `locations.conf` para configurar os caminhos de instalação - você pode misturar os tipos de instalação como bem desejar.  Apenas ip numéricos podem ser usados como URL.
*Note que todos os caminhos de diretórios devem terminar com uma barra ( / ).*

#### CARTÃO SD
Suporta a instalação pelo cartão SD.  Use a URI `sdmc:/` para apontar para o cartão SD. Subdiretórios também funcionam, como por exemplo `sdmc://nsps/`.

#### FTP
Protocolo FTP comum. FTPS não e SFTP não, apenas o protocolo FTP padrão.

#### HTTP
HTTP requer que a listagem/navegação de diretórios esteja habilitada.

#### USB
Requer um servidor `nut` configurado. Mais detalhes [aqui](https://github.com/blawar/nut/#usb-server-for-dz).

#### NUT SERVER
Requer um servidor `nut` configurado. Mais detalhes [aqui](https://github.com/blawar/nut/#server-gui). Certifique-se sempre que o servidor NUT esteja atualizado quando for usar o DZ.


## Resolução de Problemas

#### Apenas o cartão SD está na lista de locais para instalação
Ou o arquivo `locations.conf` não está no caminho correto no SD `/switch/dz/locations.conf`, ou a formatação do arquivo está incorreta, deixando-o como um JSON inválido, ou você salvou o arquivo como unicode.
- Certifique-se que o arquivo `/switch/dz/locations.conf` existe no seu cartão SD.
- Certifique-se que o arquivo `locations.conf` é um arquivo JSON válido [aqui](https://jsonlint.com/).
- Certifique-se que o arquivo `locations.conf` não foi salvo como unicode, essa formatação não é suportada.

#### Eu consigo ver uma rede na lista de locais, porém não há arquivos listados
Ou o DZ não consegue conectar à rede com as opções de rede fornecidas, ou você está usando http e não ativou a busca por diretório, ou o seu firewall está bloqueando a conexão.
- Certifique-se que você consegue conectar ao servidor FTP/HTTP/NUT usando as mesmas configurações de um computador *diferente* do que está executando o servidor.
- DZ não suporta subdiretórios, então cada caminho deve apontar exatamente para onde os arquivos NSP estão localizados.
- Certifique-se que o seu firewall permite conexões externas.  Configure ou desabilite o seu firewall.
- Se estiver usando HTTP, certifique-se que o servidor permite a visualização de arquivos. Isso deve ser feito manualmente através do IIS.

#### Eu consigo ver os arquivos, porém não consigo baixá-los.
- Certifique-se que a url no `locations.conf` termina com uma barra  ( / ).
- Se estiver usando HTTP, certifique-se que você consegue baixar o arquivo usando um navegador web.  Você deve adicionar a extensão NSP na lista de tipos MIME  (application/octet-stream) no IIS para baixar os arquivos corretamente. 

#### DZ trava em uma tela preta ao abrir
Certifique-se que as configurações de rede (especialmente o IP) estão corretas.

## Extraindo Title Keys ##

Title keys são salvas em `sdmc:/switch/dz/titlekeys.txt` quando extraídas. Além disso, você pode colocar um url HTTP no arquivo `/switch/dz/titlekeys.url.txt` para enviar automaticamente as suas keys para backup.


## Aviso

Use por sua conta e risco, e [sempre tenha um backup de sua NAND](https://gbatemp.net/threads/rcm-payload-hekate-ctcaer-mod.502604/).


# Changelog

- Adicionado log de erros CURL para a janela de console para resolução de problemas de conexão. 
- Adicionado barra de rolagem ao menu, para aqueles com muitas localizações.
- Adicionado fundo colorido em para identificar processos completos da fila.
- Corrigido problema ao instalar updates acima de 0x1000 / 65536
- Adicionado barra de rolagem ao console
- Removido ícone do Pepe.
- Corrigido pequeno bug gráfico ao usar a barra de rolagem.
- Corrigido problema gerado por nome de arquivos com naming issues with apóstrofos e ‘e comerciais’.
- Corrigido opção visualização de títulos em forma de tiles e a opção de trocar o modo de visualização de títulos. 
- Added collapsible menu when browsing the panels.
- Corrigidos alguns problemas de vazamento de memória.
- Removido o teste de versão do sistema operacional para instalações
- Corrigido erro que causava corrupção de dados.
- Otimizada a performance dos ícones da UI.
- Corrigido problemas de falta de memória durante a instalação de alguns títulos.
- Otimizado a performance de acesso à alguns tipos de arquivos.
- Velocidade de download melhorada um pouco.
- Adicionado ícones para DLC e Updates.
- Corrigido problema ao baixar pequenos DLCs.
- Adicionada janela para deletar os registros de aplicações.
- Ajustes na UI
- Adicionado opção de ordenação para diretórios em rede.
- Adicionado indicador de tamanho de arquivo e data de modificação ao usar servidores FTP.
- Adicionado Indicadores de espaço livre.
- Barras de progresso movidas para parte superior da tela
- Adicionado categorização por linguagem e versão na lista de títulos.
- Adicionada limpeza automática dos nomes dos títulos na lista.
- Corrigido problema de instalação causados por cartões de SD lentos.
- Corrigido problema ao instalar pequenos DLCs.
- Adicionado arquivo exemplo para instalação pelo cartão SD.
- Adicionada opção para instalar na NAND
- Adicionado suporte a servidores Nut
- Corrigido erro que causava uma movimentação estranha no modo de visualização por tiles.
- Aumentado o tempo para a expiração de gravação de arquivos para pessoas com cartões SD lentos.
- Movido aplicações já instaladas para cima da lista.
- Adicionada uma mensagem de erro que avisa quando o NCA não consegue ser baixado.
- Corrigido bug que causava algumas instalações via SD falharem.
- Atualizado o marcador de espaço livre após uma instalação.
- Inicio da o desenvolvimento de uma opção para ordenar títulos. Ainda bugado.
- Adicionada iluminação nas caixas de diálogo.
- Melhorado significativamente o carregamento de ícones do modo tiled.
- Corrigido erro no carregamento de ícones na tela principal.
- Adicionado opções de instalação. Apenas a escolhas de localização e de incluir DLCs estão funcionando no momento.
- Adicionado instalação experimental por USB usando o comando: `nut.py --usb` (tenha certeza de que o NUT consegue acessar os seus NSP’s)
- Adicionado coluna de categorização por tipo na lista de títulos e corrigido a coluna de regiões não sendo preenchida ao usar servidores NUT.
- Adicionado as informações dos DLCs de volta no nome para poder diferenciar eles na lista.
- Adicionado transição mais suave ao usar a barra de rolagem nos tiles.
- Adicionada aglomeração automática da lista de jogos, dlcs, and updates, escondendo os títulos já instalados.  Essa seleção aglomera todos os títulos de todas as localizações em uma única lista.
- Altera a lista aglomerada de updates para apenas mostrar versões superiores às já instaladas.
- Adicionado lista de DLCs e updates à caixa de diálogo de instalação.
- Opção para instalar o update mais novo na caixa de diálogo de instalação agora funciona.
- Adicionado suporte para carregar nomes e metadatas de títulos usando o arquivo titles.US.en.json.  Copie esse arquivo para a pasta /switch/dz/titles.US.en.json
- Alterado texto de "Data Modificada" para "Lançamento"
- Nome alterado para Tinfoil.
- Desabilitado a opção de sair com o botão B.
- Corrigido o texto "Unknown" aparecendo como nome de títulos em alguns casos.
- Otimizado a performance do carregamento de ícones.
- Adicionado modo de visualização com ícones pequenos.
- Adicionado efeito de rolagem suave à lista de títulos.


## Credits

Ideas from Adubbz:
https://github.com/Adubbz/

HACTOOL source code was reverse-engineered, with small bits of code lifted here and there:
https://github.com/SciresM/hactool

Random JSON parser:
https://github.com/nlohmann/jsonmite instalar jogos, update, e DLCs e dumpar title keys.