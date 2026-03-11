# LeadsRegiao (Extrator de Leads)

O **LeadsRegiao** é um sistema automatizado para captação de leads B2B (Business-to-Business) focado em profissionais liberais e empresas locais. Ele utiliza automação de navegação web para extrair informações públicas do Google Maps e realiza varreduras profundas nos sites das empresas para encontrar e-mails de contato. Por fim, todos os dados coletados são salvos automaticamente em uma planilha do Google Sheets.

## 🚀 Funcionalidades

- **Busca no Google Maps:** Pesquisa automatizada por categorias profissionais em cidades específicas.
- **Extração de Dados:** Coleta nome da empresa, telefone (WhatsApp), tipo de profissional e cidade.
- **Busca Profunda de E-mail (Deep Scraping):** Caso a empresa possua um site listado no Maps, o robô acessa este site em segundo plano e varre o código-fonte em busca de e-mails válidos.
- **Filtro Inteligente:** Ignora e-mails falsos (ex: imagens `.png`, `.jpg`) e e-mails de sistema (ex: `sentry`, `no-reply`).
- **Integração com Google Sheets:** Salva os leads processados e sem duplicatas diretamente em uma planilha na nuvem.
- **Interface Interativa Simples:** Menu no terminal para escolher entre rodar a extração em todas as cidades configuradas ou apenas em uma específica.

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **[Playwright](https://playwright.dev/python/):** Para automação do navegador Chromium (suporte assíncrono).
- **[gspread](https://docs.gspread.org/):** Para integração e escrita de dados na API do Google Sheets.
- **[Pydantic](https://docs.pydantic.dev/):** Para validação e estruturação dos dados (Modelagem da classe `Profissional`).
- **Asyncio:** Para execução de tarefas assíncronas de forma performática.
- **Expressões Regulares (Regex):** Para identificação padronizada de telefones e e-mails no meio de textos ou códigos HTML.

## 📋 Pré-requisitos

Antes de iniciar, certifique-se de ter instalado:

1. **Python 3.8+**
2. **Navegadores do Playwright:**
   Após instalar os pacotes Python, você deve baixar os binários do Chromium usados pelo Playwright:
   ```bash
   playwright install chromium
   ```
3. **Credenciais do Google Cloud:**
   Um arquivo `credentials.json` válido referente à uma Service Account (Conta de Serviço) do GCP com acesso à API do Google Sheets. O arquivo deve estar na mesma pasta do script principal.
4. **Planilha no Google Sheets:**
   Crie uma planilha chamada exatamente **`Leads_Profissionais`** e compartilhe o acesso de **Editor** com o e-mail da sua Service Account (encontrado em `client_email` no `credentials.json`).

## ⚙️ Como Instalar e Rodar

1. Clone ou baixe este repositório.
2. É recomendado criar um ambiente virtual (`.venv`):
   ```bash
   python -m venv .venv
   # Ative no Windows:
   .venv\Scripts\activate
   # Ative no Linux/Mac:
   source .venv/bin/activate
   ```
3. Instale as dependências. Se não houver um `requirements.txt`, as bibliotecas principais são:
   ```bash
   pip install playwright pydantic gspread
   ```
4. Instale o Chromium via Playwright (se ainda não o fez):
   ```bash
   playwright install chromium
   ```
5. Certifique-se de que o arquivo `credentials.json` está na raiz do projeto.
6. Execute o script principal:
   ```bash
   python extrator_leads.py
   ```

## 🏗️ Como Gerar o Executável (.exe)

O projeto já contém um arquivo `.spec` configurado para gerar um executável via PyInstaller (o arquivo `Extrator_Leads_SP.spec`). O código também conta com tratamento para buscar o arquivo `credentials.json` no diretório correto caso o script esteja "congelado" (frozen).

Para gerar o arquivo `.exe` stand-alone:

```bash
pip install pyinstaller
pyinstaller Extrator_Leads_SP.spec
```
O executável final estará disponível dentro da pasta `dist/`. Basta colocá-lo na mesma pasta que o seu `credentials.json` para executá-lo sem precisar do Python instalado localmente.

## ⚠️ Avisos e Boas Práticas

- O Playwright inicia nativamente no modo `headless=False` (tela visível). Para rodar em segundo plano, você pode alterar essa configuração no código (`browser = await p.chromium.launch(headless=True)`).
- Faça uso consciente. Consultas extremamente agressivas e rápidas no Google Maps podem resultar em bloqueios temporários (CAPTCHA ou Soft-Bans de IP).

---
