# Canhoto Digital API

Sistema de Canhoto Digital (NF-e)

Este README está disponível em: Português (BR) | [English](README.en.md)

## Requisitos

Este projeto requer:

- Python 3.12
- PostgreSQL 9.3+
- Redis (para broker do Celery em ambiente local)
- Git
- virtualenvwrapper, pyenv virtualenv ou virtualenv para desenvolvimento local

## Instalação

### 1. Clonar o repositório

```shell
$ git clone <repository-url>
$ cd canhoto_digital
```

### 2. Preparar o ambiente Python

Usando pyenv (recomendado):

```shell
# Instale o pyenv se ainda não tiver
$ curl https://pyenv.run | bash
$ export PATH="$HOME/.pyenv/bin:$PATH"
$ eval "$(pyenv init -)"
$ eval "$(pyenv virtualenv-init -)"

# Reinicie o terminal ou rode
$ exec "$SHELL"

# Instale o Python 3.12 e crie o ambiente virtual
$ pyenv install 3.12.0
$ pyenv virtualenv 3.12.0 canhoto_digital
$ pyenv activate canhoto_digital
```

### 3. Instalar dependências

```shell
$ pip install -r requirements/local.txt
```

Ou usando make:

```shell
$ make deps
```

### 4. Configurar variáveis de ambiente

```shell
$ cp local.env .env
# Edite o arquivo .env com suas configurações locais
```

### 5. Preparar o banco de dados

```shell
$ python src/manage.py migrate
```

Ou usando make:

```shell
$ make migrate
```

### 6. Criar superusuário (opcional)

```shell
$ python src/manage.py createsuperuser
```

## Desenvolvimento

### Executar o servidor de desenvolvimento localmente

```shell
$ python src/manage.py runserver
```

Ou usando make:

```shell
$ make run
```

A API ficará disponível em `http://localhost:8000/`

### Executar com Docker

```shell
$ docker compose up --build
# admin: http://localhost:8000/admin
```

### Executar o worker do Celery

Para processamento assíncrono de tarefas:

```shell
$ make celery
```

Ou manualmente:

```shell
$ cd src
$ celery -A proj_settings worker --loglevel=info
```

### Comandos Make disponíveis

- `make deps` - Instalar dependências
- `make run` - Executar o servidor de desenvolvimento
- `make migrate` - Aplicar migrações do banco
- `make migrations` - Criar novas migrações
- `make test` - Executar testes
- `make celery` - Iniciar o worker do Celery
- `make clean` - Limpar arquivos temporários

## Testes

Utilizamos `pytest` com plugins adicionais para uma cobertura abrangente.

Executar todos os testes:

```shell
$ cd src
$ pytest -vv -s
```

Executar testes com cobertura:

```shell
$ cd src
$ pytest --cov=apps --cov-report=html
```

## Integração com SEFAZ — Como usar

O projeto inclui uma integração real com a distribuição DF-e da SEFAZ para buscar as últimas notas da sua empresa. O cliente está em `src/apps/invoice/sefaz/` e é utilizado por uma ação do Admin e por uma tarefa Celery.

### Pré-requisitos
- Um registro de Empresa (Company) com os campos abaixo preenchidos:
  - `cnpj` (somente números)
  - `uf` (estado)
  - `sefaz_environment` ("production" ou "homologation")
  - `certificate` (arquivo A1 e-CNPJ: .pfx ou .p12)
  - `certificate_password`
- Worker do Celery em execução.
- Configuração opcional (já padronizada): `SEFAZ_HTTP_TIMEOUT_SECONDS` em `proj_settings.settings` para ajustar o timeout HTTP (padrão: 60 segundos).

### Opção 1 — Importar via Django Admin
1) Vá ao Admin → Invoices.
2) Clique em "Import from SEFAZ" nas ações do canto superior direito.
3) Preencha o formulário: Empresa e intervalo de datas.
4) Envie. Uma tarefa Celery será enfileirada e o progresso aparecerá nos logs do Celery.

As notas que coincidirem com o período selecionado serão criadas/atualizadas no modelo `Invoice`. O campo `last_nsu` da empresa é atualizado conforme os lotes são processados.

### Opção 2 — Importar programaticamente (tarefa Celery)
Você pode disparar a mesma tarefa programaticamente, por exemplo, pelo shell do Django:

```python
from datetime import date
from apps.company.models import Company
from apps.invoice.tasks import import_from_sefaz

company = Company.objects.get(cnpj="00000000000000")  # substitua pelo seu CNPJ
res = import_from_sefaz.delay(company.id, date(2025, 1, 1).isoformat(), date(2025, 1, 31).isoformat())
print(res.id)  # id da tarefa Celery
```

Quando a tarefa termina, ela retorna um payload como `{ "created": X, "updated": Y }`.

### Notas
- A integração usa o endpoint nacional oficial de DF-e via SOAP com mTLS (certificado de cliente). Não são necessários provedores pagos.
- A SEFAZ pode retornar documentos de resumo (`resNFe`) ou NF-e completa (`procNFe`). O importador mapeia os dados disponíveis para os campos de `Invoice`; arquivos XML/PDF não são persistidos por padrão.
- O cursor de NSU (`company.last_nsu`) avança mesmo que nenhuma nota caia dentro do filtro de datas escolhido, evitando reprocessar lotes antigos.
- Se você trocar o ambiente (homologação/produção) ou o certificado, pode ser necessário resetar o `last_nsu` para `0`.
- Erros aparecerão nas mensagens do Admin ou nos logs do Celery. Verifique a validade do certificado e a senha em caso de erros de TLS.

## Licença

Este software é licenciado para uso sob um contrato comercial da h-devs. Ao utilizar o software, você concorda com os termos da [EULA (Português)](EULA.pt-BR.md) ou [EULA (English)](EULA.en.md).

Direitos autorais © 2025 h-devs. Todos os direitos reservados. Para licenciamento comercial, contate: legal@h-devs.com
