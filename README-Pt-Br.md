# Nut
Este é um programa que baixa automaticamente todos os jogos da CDN, e os organiza no sistema de arquivos como backups. Você pode jogar apenas os jogos que você comprou legalmente / tem a title key. Nut também fornece uma interface web para navegar em sua coleção.

Você deve copiar o nut.default.conf para nut.conf e fazer todas as suas edições locais no nut.conf.

**Se você deseja apenas renomear / organizar os arquivos, e não baixar nada, edite `nut.conf` modificando todas as opções de download para 'false'.** Seus arquivos NSP devem ter o titleid entre colchetes como parte do nome de arquivo.

É possível baixar qualquer título sem a chave (para arquivar), habilitando a opção `sansTitleKey` no `nut.conf`. Estes títulos são salvos com a extensão `.nsx`, e pode ser destravado posteriormente quando a title key for encontrada.

![alt text](https://raw.githubusercontent.com/blawar/nut/master/public_html/images/ss.jpg)

---------

## Uso
 - Download [`nut`](https://github.com/blawar/nut/archive/master.zip)
 - Se você deseja baixar da CDN, coloque tudo em seu já configurado diretório CDNSP. Você vai precisar especificamente de:
	- `Certificate.cert`
	- `nx_tls_client_cert.pem`
	- `keys.txt`
 - Python 3.6+ instalado
 - Instale os seguintes módulos via `pip`:
 	 - `pip3 install colorama pyopenssl requests tqdm unidecode image bs4 urllib3 flask`
 - Configure o `nut.conf` (veja abaixo)
 - Rode o comando `python3 nut.py --help` para entender as opções.
 
 ## USB Server para o DZ
Garanta que o nut está configurado corretamente para ver seus NSP's, e rode o seguinte comando para entrar no modo USB Server: nut.py --usb

## Server GUI
Se você desejar iniciar uma interface gráfica para o servidor, você deve primeiro baixar as imagens da nintendo. Você pode fazer isso com o comando:
nut.py -s --scrape

Isso vai levar um tempo. Quando estiver concluído, você pode iniciar o servidor web com:
nut.py --server

Então acessar via navegador web com o endereço localhost:9000

---------

## Configuração
Toda configuração é feita via `nut.conf`.

### Caminhos
Configure como você quer que o `nut` armazene (e organize) seus arquivos. Por padrão:
```
Base Games:		titles/{name}[{id}][v{version}].nsp
DLC:			titles/DLC/{name}[{id}][v{version}].nsp
Updates:		titles/updates/{name}[{id}][v{version}].nsp
Demos: 			titles/demos/{name}[{id}][v{version}].nsp
Demo Updates:		titles/demos/updates/{name}[{id}][v{version}].nsp

nspOut			_NSPOUT
scan (folder)		.
```

### Lista de Títulos
`nut` irá baixar, analizar, e combinar listas de titlekey para URLs definida em `titleUrls` e `titledb\*.txt`. Eles serão carregados preferencialmente: primeiro listas locais (em ordem alfabética), então listas remotas. Isso é útil no caso você queira manter nomes de títulos customizados (ex. em um `titledb\z.titlekeys.txt`)

Formatos aceitáveis: 
```
Rights ID|Title Key|Title Name
01000320000cc0000000000000000000|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|1-2-Switch

ou

id|rightsId|key|isUpdate|isDLC|isDemo|name|version|region|retailOnly
01000320000cc000|01000320000cc0000000000000000000|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|0|0|0|1-2-Switch™|0|US|0

ou

id|name
01000320000cc000|1-2-Switch™

etc
```

### Whitelist
Coloque qualquer title id que você queira baixar em `whitelist.txt`, separados por novas linhas.

*Se você quer baixar todos os jogos, deixe o arquivo vazio.*

### Blacklist
Coloque qualquer title id que você **não** quer baixar em `blacklist.txt`, separados por novas linhas.

# Ajuda
(partes traduzidas, mas ao usar o comando nut.py -h, você verá a ajuda escrita em seu idioma original).
```
nut.py -h
uso: nut.py [-h] [--base {0,1}] [--demo {0,1}] [--update {0,1}]
              [--dlc {0,1}] [--nsx {0,1}] [-D] [-d DOWNLOAD [DOWNLOAD ...]]
              [-i INFO] [-u UNLOCK] [--unlock-all]
              [--set-masterkey1 SET_MASTERKEY1]
              [--set-masterkey2 SET_MASTERKEY2]
              [--set-masterkey3 SET_MASTERKEY3]
              [--set-masterkey4 SET_MASTERKEY4]
              [--set-masterkey5 SET_MASTERKEY5]
              [--remove-title-rights REMOVE_TITLE_RIGHTS] [-s] [-Z] [-z] [-V]
              [-o] [-U] [-r] [-x EXTRACT [EXTRACT ...]] [-c CREATE]
              [--export-missing EXPORT_MISSING] [-M MISSING]
              [--nca-deltas NCA_DELTAS] [--silent] [--json] [-S] [-m] [-p]
              [--scrape] [--scrape-delta] [--scrape-title SCRAPE_TITLE]
              [file [file ...]]

argumentos posicionais:
  file

argumentos opcionais:
  -h, --help            mostra este texto de ajuda e finaliza.
  --base {0,1}          baixa todos os títulos base
  --demo {0,1}          baixa todos os títulos demo
  --update {0,1}        baixa todos os updates de títulos
  --dlc {0,1}           baixa todos os DLC de títulos
  --nsx {0,1}           baixa todos os títulos sem chave
  -D, --download-all    baixa TODOS os títulos
  -d DOWNLOAD [DOWNLOAD ...], --download DOWNLOAD [DOWNLOAD ...]
                        download title(s)
  -i INFO, --info INFO  mostra informação sobre título ou arquivo
  -u UNLOCK, --unlock UNLOCK
                        instala os title keys disponíveis em NSX / NSP
  --unlock-all          instala os title keys disponiveis em todos os arquivos NSX
  --set-masterkey1 SET_MASTERKEY1
                        Muda a master key encryption para NSP.
  --set-masterkey2 SET_MASTERKEY2
                        Muda a master key encryption para NSP.
  --set-masterkey3 SET_MASTERKEY3
                        Muda a master key encryption para NSP.
  --set-masterkey4 SET_MASTERKEY4
                        Muda a master key encryption para NSP.
  --set-masterkey5 SET_MASTERKEY5
                        Muda a master key encryption para NSP.
  --remove-title-rights REMOVE_TITLE_RIGHTS
                        Remove a criptografia de direitos de propriedade de todos os NCAs.
                        NSP.
  -s, --scan            sonda por novos arquivos NSP
  -Z                    atualizar todas as versões do título da nintendo
  -z                    update newest title versions from nintendo
  -V                    atualize as novas versões de títulos da nintendo
  -o, --organize        renomea e move todos os arquivos NSP
  -U, --update-titles   atualizar títulos db de urls
  -r, --refresh         lê todos os meta de arquivos NSP e consulta a CDN para
                        informações de versão mais recentes
  -x EXTRACT [EXTRACT ...], --extract EXTRACT [EXTRACT ...]
                        extrai / desempacota a NSP
  -c CREATE, --create CREATE
                        cria / empacota a NSP
  --export-missing EXPORT_MISSING
                        exporta o banco de dados de titulos em formato csv
  -M MISSING, --missing MISSING
                        exporta o banco de dados de titulos que você não
                        baixou em formato csv
  --nca-deltas NCA_DELTAS
                        exporta list de NSPs contendo os delta updates
  --silent              Silencia a saída stdout/stderr
  --json                JSON output
  -S, --server          Execute o daemon do servidor
  -m, --hostname        Define o nome do host do servidor
  -p, --port            Define a porta do servidor
  --scrape              Extrai TODOS os títulos dos servidores da Nintendo
  --scrape-delta        Raspe TODOS os títulos dos servidores da Nintendo que você
                        ainda não extraiu
  --scrape-title SCRAPE_TITLE
                        Extrai título do servidor da Nintendo
```

# Créditos
- CDNSP Original
- Hactool por SciresM (https://github.com/SciresM/)
- Simon (https://github.com/simontime/) por seu conhecimento e ajuda aparentemente intermináveis ​​de CDN.
