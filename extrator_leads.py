import os
import sys
import asyncio
import re
from typing import List, Optional
from pydantic import BaseModel
from playwright.async_api import async_playwright
import gspread

# --- 1. UTILITÁRIOS ---
def obter_caminho_credenciais() -> str:
    if getattr(sys, 'frozen', False):
        diretorio_base = os.path.dirname(sys.executable)
    else:
        diretorio_base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(diretorio_base, 'credentials.json')

# --- 2. MODELO DE DADOS ---
class Profissional(BaseModel):
    nome_empresa: str
    email: Optional[str] = "Não encontrado"
    telefone_whatsapp: Optional[str] = "Não encontrado"
    tipo_profissional: str
    cidade: str

# --- 3. GOOGLE SHEETS ---
def salvar_no_sheets(dados: List[Profissional]):
    try:
        caminho_json = obter_caminho_credenciais()
        if not os.path.exists(caminho_json):
            print(f"❌ Erro: Arquivo {caminho_json} não encontrado.")
            return

        gc = gspread.service_account(filename=caminho_json)
        planilha = gc.open("Leads_Profissionais").sheet1
        
        for item in dados:
            planilha.append_row([item.nome_empresa, item.email, item.telefone_whatsapp, item.tipo_profissional, item.cidade])
            
        print(f"✅ {len(dados)} leads salvos na planilha.")
    except Exception as e:
        print(f"❌ Erro no Sheets: {e}")

# --- 4. EXTRATOR PROFUNDO DE E-MAILS (SITE) ---
async def extrair_email_do_site(context, url_base: str) -> Optional[str]:
    """Cria uma aba temporária, acessa o site e varre o texto buscando padrão de e-mail"""
    aba = None
    try:
        aba = await context.new_page()
        # Tempo de vida curto para não travar: carrega apenas o corpo rápido
        await aba.goto(url_base, timeout=12000, wait_until="domcontentloaded")
        texto_pagina = await aba.content()
        
        # Regex melhorada (ignora e-mails falsos como png/jpg)
        padrao = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?!png|jpg|jpeg|gif|webp)[a-zA-Z]{2,}'
        emails_encontrados = re.findall(padrao, texto_pagina)
        
        # Filtra lixos de frameworks comuns (ex: wix, wordpress core, react)
        emails_validos = [e for e in emails_encontrados if not e.startswith(("sentry", "no-reply"))]
        
        return emails_validos[0] if emails_validos else None
    except Exception as e:
        # Se o site for inválido ou der timeout, segue a vida
        return None
    finally:
        if aba:
            await aba.close()

# --- 5. MOTOR DE MÁXIMA EXTRAÇÃO (GOOGLE MAPS) ---
async def buscar_profissionais(profissao: str, cidade: str) -> List[Profissional]:
    lista_contatos = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        search_query = f"{profissao} em {cidade} SP"
        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        await page.goto(url)
        await page.wait_for_timeout(5000) 

        # Rolar a barra lateral para carregar mais resultados focando no último elemento
        try:
            for _ in range(10): # Tenta rolar 10 vezes (pode aumentar se quiser mais leads)
                elementos = await page.query_selector_all('a[href*="/maps/place/"]')
                if elementos:
                    ultimo_elemento = elementos[-1]
                    await ultimo_elemento.scroll_into_view_if_needed()
                    await page.wait_for_timeout(1500) # Tempo para o Maps carregar a próxima página invisível
        except Exception:
            pass

        # Seletores baseados em atributos explícitos de links tendem a ser mais duradouros
        cards = await page.query_selector_all('a[href*="/maps/place/"]')
        for card in cards:
            try:
                nome = await card.get_attribute('aria-label')
                if not nome:
                    continue
                
                parent = await card.evaluate_handle('el => el.parentElement ? el.parentElement.parentElement : el')
                info_texto = await parent.inner_text() if parent else ""
                
                # Telefone
                phone_match = re.search(r'(\(?\d{2}\)?\s?\d{4,5}-?\d{4})', info_texto)
                telefone = phone_match.group(0) if phone_match else "Não encontrado"
                
                # Vamos tentar encontrar se existe botão de site para a empresa
                link_site = await parent.query_selector('a[data-value="Ligar site"]') 
                # Dependendo do idioma do Google, pode variar a label (pt/en). 
                # Uma busca alternativa pelo ícone "website":
                if not link_site:
                    botoes_acao = await parent.query_selector_all('a[href^="http"]')
                    for b in botoes_acao:
                        href = await b.get_attribute('href')
                        if href and "google.com" not in href:
                            link_site = href
                            break
                    else:
                        link_site = None
                else:
                    link_site = await link_site.get_attribute('href')
                
                email = "Não localizado"
                if link_site:
                    try:
                        link_str = str(link_site)
                        recorte = link_str[0:40] # type: ignore
                        print(f"   [Busca Profunda] Site de {nome} encontrado. Varrendo: {recorte}...")

                        
                        email_achado = await extrair_email_do_site(context, link_str)
                        if email_achado:
                            email = email_achado
                            print(f"      -> E-mail capturado com sucesso: {email}")
                    except Exception:
                        pass

                # Backup: Se o site falhou, tenta catar na descrição curta do G-Maps
                if email == "Não localizado":
                    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', info_texto)
                    email = email_match.group(0) if email_match else "Não localizado (Sem site/Inválido)"

                lista_contatos.append(Profissional(
                    nome_empresa=nome,
                    email=email,
                    telefone_whatsapp=telefone,
                    tipo_profissional=profissao,
                    cidade=cidade
                ))
            except Exception:
                continue

        await browser.close()
        
    # Removendo contatos duplicados
    unicos = {c.nome_empresa: c for c in lista_contatos}
    return list(unicos.values())

# --- 5. ORQUESTRADOR E MENU ---
async def executar_scraping(profissoes: List[str], cidades: List[str]):
    for cidade in cidades:
        for profissao in profissoes:
            print(f"\n🚀 Iniciando: {profissao} em {cidade}")
            leads = await buscar_profissionais(profissao, cidade)
            if leads:
                salvar_no_sheets(leads)
            await asyncio.sleep(2)

def main():
    print("=== SISTEMA DE CAPTAÇÃO DE LEADS (ANTIGRAVITY) ===")
    profissoes = ["Médico", "Advogado", "Nutricionista", "Veterinário", "Arquiteto"]
    cidades = ["Valinhos", "Vinhedo", "Campinas"]

    print("\nCidades disponíveis:", ", ".join(cidades))
    print("Profissões disponíveis:", ", ".join(profissoes))
    
    escolha = input("\nDeseja rodar (1) Tudo ou (2) Apenas uma cidade específica? ")

    if escolha == "2":
        cidade_alvo = input("Digite o nome da cidade (ex: Valinhos): ").capitalize()
        if cidade_alvo in cidades:
            cidades = [cidade_alvo]
        else:
            print("Cidade não mapeada. Rodando para todas.")

    # O loop assíncrono só inicia depois dos inputs síncronos acabarem.
    asyncio.run(executar_scraping(profissoes, cidades))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcesso interrompido pelo usuário.")