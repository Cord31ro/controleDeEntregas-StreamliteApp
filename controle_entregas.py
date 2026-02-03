import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import time

# =====================================================
# CONFIGURAÇÕES
# =====================================================

st.set_page_config(
    page_title="Controle de Entregas - Obra",
    page_icon="🏗️",
    layout="wide"
)

# URL da planilha
SHEET_URL = "https://docs.google.com/spreadsheets/d/17pK_8AgmQISuaLGdZD5FoiQzQBlPKOY6YV2Xh96RCqs"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =====================================================
# MUNICÍPIOS E MATERIAIS
# =====================================================

MUNICIPIOS = [
    "São Vicente do Seridó",
    "Pedra Lavrada",
]

MATERIAIS_PADRAO = [
    "Tijolo (1000 un)",
    "Brita (5 m³)",
    "Areia (5 m³)",
    "Cimento (50 sacos)",
    "Cal (20 sacos)",
    "Ferro 8mm (50 barras)",
    "Ferro 10mm (50 barras)",
]

# =====================================================
# USUÁRIOS
# =====================================================

USUARIOS = {
    "gutemberg": {
        "nome": "Gutemberg Martins",
        "pin": "0000",
        "admin": True
    },
    "severino": {
        "nome": "Severino Cordeiro",
        "pin": "0101",
        "admin": False
    },
    "virgilho": {
        "nome": "Virgilho Cordeiro",
        "pin": "0209",
        "admin": False
    },
    "gutemberg_filho": {
        "nome": "Gutemberg Filho",
        "pin": "2004",
        "admin": False
    },
}

# =====================================================
# FUNÇÕES DO GOOGLE SHEETS COM CACHE
# =====================================================

@st.cache_resource
def conectar_google_sheets():
    """Conecta ao Google Sheets"""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Corrige a private_key se necessário
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )
        
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return None


def inicializar_planilha(client):
    """Cria as abas necessárias se não existirem - APENAS UMA VEZ"""
    if not client:
        return None
    
    # Verifica se já foi inicializado nesta sessão
    if "planilha_inicializada" in st.session_state:
        return st.session_state.planilha_inicializada
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        
        # Verifica/Cria aba de Casas
        try:
            ws_casas = sheet.worksheet("Casas")
        except:
            ws_casas = sheet.add_worksheet(title="Casas", rows=1000, cols=10)
            ws_casas.update('A1', [["Município", "Casa", "Data Cadastro", "Cadastrado Por"]])
            time.sleep(1)
        
        # Verifica/Cria aba de Entregas
        try:
            ws_entregas = sheet.worksheet("Entregas")
        except:
            ws_entregas = sheet.add_worksheet(title="Entregas", rows=5000, cols=10)
            ws_entregas.update('A1', [["Município", "Casa", "Material", "Entregue", "Data Entrega", "Confirmado Por"]])
            time.sleep(1)
        
        # Salva no session_state para não precisar verificar novamente
        st.session_state.planilha_inicializada = sheet
        return sheet
    except Exception as e:
        st.error(f"Erro ao inicializar planilha: {e}")
        return None


def carregar_todos_dados(client):
    """Carrega TODOS os dados de uma vez só - OTIMIZADO"""
    if not client:
        return None, None
    
    # Verifica se já carregou recentemente (cache de 30 segundos)
    agora = time.time()
    if "ultimo_carregamento" in st.session_state:
        tempo_decorrido = agora - st.session_state.ultimo_carregamento
        if tempo_decorrido < 30:
            return st.session_state.dados_casas, st.session_state.dados_entregas
    
    try:
        sheet = client.open_by_url(SHEET_URL)
        
        ws_casas = sheet.worksheet("Casas")
        dados_casas = ws_casas.get_all_values()
        
        time.sleep(1)
        
        ws_entregas = sheet.worksheet("Entregas")
        dados_entregas = ws_entregas.get_all_values()
        
        # Salva no cache
        st.session_state.dados_casas = dados_casas
        st.session_state.dados_entregas = dados_entregas
        st.session_state.ultimo_carregamento = agora
        
        return dados_casas, dados_entregas
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None, None


def processar_casas(dados_casas):
    """Processa os dados de casas já carregados"""
    if not dados_casas or len(dados_casas) <= 1:
        return {}
    
    casas_por_municipio = {}
    for linha in dados_casas[1:]:  # Pula cabeçalho
        if len(linha) >= 2:
            municipio = linha[0]
            casa = linha[1]
            
            if municipio not in casas_por_municipio:
                casas_por_municipio[municipio] = []
            
            if casa not in casas_por_municipio[municipio]:
                casas_por_municipio[municipio].append(casa)
    
    return casas_por_municipio


def processar_entregas(dados_entregas, municipio, casa):
    """Processa as entregas de uma casa específica dos dados já carregados"""
    if not dados_entregas or len(dados_entregas) <= 1:
        return []
    
    entregas = []
    for i, linha in enumerate(dados_entregas[1:], start=2):  # Pula cabeçalho, começa da linha 2
        if len(linha) >= 6:
            if linha[0] == municipio and linha[1] == casa:
                entregas.append({
                    "linha": i,
                    "material": linha[2],
                    "entregue": linha[3] == "Sim",
                    "data_entrega": linha[4],
                    "confirmado_por": linha[5]
                })
    
    return entregas


def adicionar_casa(client, municipio, casa, usuario):
    """Adiciona uma nova casa na planilha"""
    if not client:
        return False, "Cliente do Google Sheets não inicializado"
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_casas = sheet.worksheet("Casas")
        ws_entregas = sheet.worksheet("Entregas")
        
        # Verifica se a casa já existe nos dados em cache
        dados_casas = st.session_state.get("dados_casas", [])
        if len(dados_casas) > 1:
            for linha in dados_casas[1:]:
                if len(linha) >= 2:
                    if linha[0].strip().lower() == municipio.strip().lower() and linha[1].strip().lower() == casa.strip().lower():
                        return False, "Casa já cadastrada neste município!"
        
        # Adiciona a casa
        data_cadastro = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ws_casas.append_row([municipio, casa, data_cadastro, usuario])
        time.sleep(1)
        
        # Adiciona os materiais padrão para esta casa
        linhas_materiais = []
        for material in MATERIAIS_PADRAO:
            linhas_materiais.append([municipio, casa, material, "Não", "", ""])
        
        # Adiciona todos os materiais de uma vez
        ws_entregas.append_rows(linhas_materiais)
        
        # Limpa o cache para forçar recarga
        if "ultimo_carregamento" in st.session_state:
            del st.session_state.ultimo_carregamento
        
        return True, f"✅ Casa '{casa}' adicionada com sucesso em {municipio}!"
    except Exception as e:
        import traceback
        erro_completo = traceback.format_exc()
        return False, f"Erro ao adicionar casa: {str(e)}\n\nDetalhes: {erro_completo}"


def marcar_entrega(client, linha, material, usuario):
    """Marca um material como entregue"""
    if not client:
        return False, "Cliente do Google Sheets não inicializado"
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_entregas = sheet.worksheet("Entregas")
        
        data_entrega = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ws_entregas.update(f'D{linha}:F{linha}', [["Sim", data_entrega, usuario]])
        
        # Limpa o cache
        if "ultimo_carregamento" in st.session_state:
            del st.session_state.ultimo_carregamento
        
        return True, "Entrega confirmada!"
    except Exception as e:
        return False, f"Erro ao marcar entrega: {e}"


def desmarcar_entrega(client, linha):
    """Desmarca um material como entregue"""
    if not client:
        return False, "Cliente do Google Sheets não inicializado"
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_entregas = sheet.worksheet("Entregas")
        
        ws_entregas.update(f'D{linha}:F{linha}', [["Não", "", ""]])
        
        # Limpa o cache
        if "ultimo_carregamento" in st.session_state:
            del st.session_state.ultimo_carregamento
        
        return True, "Entrega desmarcada!"
    except Exception as e:
        return False, f"Erro ao desmarcar entrega: {e}"


# =====================================================
# FUNÇÕES DE AUTENTICAÇÃO
# =====================================================

def hash_pin(pin):
    """Hash simples do PIN"""
    return hashlib.sha256(pin.encode()).hexdigest()


def verificar_login(username, pin):
    """Verifica se o login é válido"""
    if username in USUARIOS:
        pin_hash_correto = hash_pin(USUARIOS[username]["pin"])
        pin_hash_digitado = hash_pin(pin)
        return pin_hash_correto == pin_hash_digitado
    return False


# =====================================================
# INTERFACE - LOGIN
# =====================================================

def tela_login():
    """Tela de login"""
    st.title("🔐 Login - Controle de Entregas")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        
        usernames = list(USUARIOS.keys())
        nomes = [USUARIOS[u]["nome"] for u in usernames]
        
        opcao = st.selectbox("Selecione o usuário", nomes)
        username = usernames[nomes.index(opcao)]
        
        pin = st.text_input("Digite seu PIN", type="password", max_chars=4)
        
        if st.button("Entrar", use_container_width=True):
            if verificar_login(username, pin):
                st.session_state.usuario = username
                st.session_state.nome_usuario = USUARIOS[username]["nome"]
                st.session_state.is_admin = USUARIOS[username]["admin"]
                st.success(f"Bem-vindo, {USUARIOS[username]['nome']}!")
                st.rerun()
            else:
                st.error("❌ PIN incorreto!")
        
        st.markdown("---")


# =====================================================
# INTERFACE - PRINCIPAL
# =====================================================

def tela_principal():
    """Tela principal do sistema"""
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏗️ Controle de Entregas de Material")
    with col2:
        st.write(f"**Usuário:** {st.session_state.nome_usuario}")
        if st.button("Sair"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    st.markdown("---")
    
    # Conecta ao Google Sheets
    client = st.session_state.get("gs_client")
    
    if not client:
        st.error("❌ Erro ao conectar com Google Sheets.")
        st.info("👉 Verifique as credenciais em Settings → Secrets")
        return
    
    # Inicializa a planilha (só uma vez)
    sheet_result = inicializar_planilha(client)
    if not sheet_result:
        st.error("❌ Erro ao acessar a planilha.")
        return
    
    # CARREGA TODOS OS DADOS UMA ÚNICA VEZ
    with st.spinner("Carregando dados..."):
        dados_casas, dados_entregas = carregar_todos_dados(client)
    
    if dados_casas is None or dados_entregas is None:
        st.error("❌ Erro ao carregar dados da planilha.")
        return
    
    # Processa os dados
    casas_por_municipio = processar_casas(dados_casas)
    
    # Botão para recarregar manualmente
    if st.button("🔄 Recarregar Dados"):
        if "ultimo_carregamento" in st.session_state:
            del st.session_state.ultimo_carregamento
        st.rerun()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Controle de Entregas", "🏠 Adicionar Casa", "📊 Relatório"])
    
    # ===== TAB 1: CONTROLE DE ENTREGAS =====
    with tab1:
        st.subheader("Controle de Entregas")
        
        if not casas_por_municipio:
            st.info("Nenhuma casa cadastrada ainda. Adicione casas na aba 'Adicionar Casa'.")
        else:
            # Seleção de município
            municipio_selecionado = st.selectbox("Selecione o Município", MUNICIPIOS)
            
            if municipio_selecionado in casas_por_municipio:
                casas = casas_por_municipio[municipio_selecionado]
                
                # Exibe cada casa
                for casa in casas:
                    with st.expander(f"🏠 {casa}", expanded=False):
                        entregas = processar_entregas(dados_entregas, municipio_selecionado, casa)
                        
                        if not entregas:
                            st.warning("Nenhum material cadastrado para esta casa.")
                            continue
                        
                        # Cabeçalho
                        col1, col2, col3, col4 = st.columns([3, 1, 2, 2])
                        col1.write("**Material**")
                        col2.write("**Status**")
                        col3.write("**Data Entrega**")
                        col4.write("**Confirmado Por**")
                        
                        st.markdown("---")
                        
                        # Lista de materiais
                        for item in entregas:
                            col1, col2, col3, col4 = st.columns([3, 1, 2, 2])
                            
                            with col1:
                                st.write(item["material"])
                            
                            with col2:
                                # Usa botão ao invés de checkbox para evitar dessync de estado
                                if item["entregue"]:
                                    # Já está entregue → botão para DESMARCAR
                                    if st.button(
                                        "✅ Entregue",
                                        key=f"btn_{municipio_selecionado}_{casa}_{item['linha']}",
                                        type="primary",
                                        use_container_width=True
                                    ):
                                        sucesso, msg = desmarcar_entrega(client, item["linha"])
                                        if sucesso:
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                else:
                                    # Ainda não entregue → botão para MARCAR
                                    if st.button(
                                        "❌ Pendente",
                                        key=f"btn_{municipio_selecionado}_{casa}_{item['linha']}",
                                        type="secondary",
                                        use_container_width=True
                                    ):
                                        sucesso, msg = marcar_entrega(
                                            client,
                                            item["linha"],
                                            item["material"],
                                            st.session_state.nome_usuario
                                        )
                                        if sucesso:
                                            st.rerun()
                                        else:
                                            st.error(msg)
                            
                            with col3:
                                if item["entregue"]:
                                    st.write(f"📅 {item['data_entrega']}")
                                else:
                                    st.write("Pendente")
                            
                            with col4:
                                if item["entregue"]:
                                    st.write(f"👤 {item['confirmado_por']}")
                                else:
                                    st.write("-")
                        
                        # Estatísticas
                        total = len(entregas)
                        entregues = sum(1 for e in entregas if e["entregue"])
                        pendentes = total - entregues
                        
                        st.markdown("---")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Total", total)
                        col2.metric("Entregues", entregues)
                        col3.metric("Pendentes", pendentes)
            else:
                st.info(f"Nenhuma casa cadastrada em {municipio_selecionado}")
    
    # ===== TAB 2: ADICIONAR CASA =====
    with tab2:
        st.subheader("➕ Adicionar Nova Casa")
        
        st.info("💡 Preencha os dados abaixo para cadastrar uma nova casa e seus materiais")
        
        col1, col2 = st.columns(2)
        
        with col1:
            municipio_novo = st.selectbox("📍 Município", MUNICIPIOS, key="municipio_novo")
        
        with col2:
            casa_nova = st.text_input("🏠 Nome/Número da Casa", placeholder="Ex: Casa 01, Rua A nº 123")
        
        st.markdown("---")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            adicionar = st.button("➕ Adicionar Casa", use_container_width=True, type="primary")
        
        with col2:
            st.caption("Ao adicionar, serão criados automaticamente os registros de todos os materiais padrão para esta casa.")
        
        if adicionar:
            if not casa_nova or not casa_nova.strip():
                st.error("❌ Por favor, dixon o nome da casa!")
            else:
                with st.spinner("Adicionando casa..."):
                    sucesso, msg = adicionar_casa(
                        client, 
                        municipio_novo, 
                        casa_nova.strip(), 
                        st.session_state.nome_usuario
                    )
                    
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(msg)
        
        # Mostra as casas já cadastradas
        st.markdown("---")
        st.subheader("📋 Casas Cadastradas")
        
        if casas_por_municipio:
            for mun in MUNICIPIOS:
                if mun in casas_por_municipio and casas_por_municipio[mun]:
                    with st.expander(f"📍 {mun} ({len(casas_por_municipio[mun])} casas)"):
                        for idx, casa_nome in enumerate(casas_por_municipio[mun], 1):
                            st.write(f"{idx}. {casa_nome}")
        else:
            st.info("Nenhuma casa cadastrada ainda.")
    
    # ===== TAB 3: RELATÓRIO =====
    with tab3:
        st.subheader("📊 Relatório de Entregas")
        
        if not casas_por_municipio:
            st.info("Nenhum dado disponível.")
            return
        
        # Dados para o relatório
        dados_relatorio = []
        
        for municipio in MUNICIPIOS:
            if municipio in casas_por_municipio:
                for casa in casas_por_municipio[municipio]:
                    entregas = processar_entregas(dados_entregas, municipio, casa)
                    
                    total = len(entregas)
                    entregues = sum(1 for e in entregas if e["entregue"])
                    pendentes = total - entregues
                    percentual = (entregues / total * 100) if total > 0 else 0
                    
                    dados_relatorio.append({
                        "Município": municipio,
                        "Casa": casa,
                        "Total": total,
                        "Entregues": entregues,
                        "Pendentes": pendentes,
                        "% Concluído": f"{percentual:.1f}%"
                    })
        
        if dados_relatorio:
            df = pd.DataFrame(dados_relatorio)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Resumo geral
            st.markdown("---")
            st.subheader("📈 Resumo Geral")
            
            total_geral = sum(d["Total"] for d in dados_relatorio)
            entregues_geral = sum(d["Entregues"] for d in dados_relatorio)
            pendentes_geral = sum(d["Pendentes"] for d in dados_relatorio)
            perc_geral = (entregues_geral / total_geral * 100) if total_geral > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Materiais", total_geral)
            col2.metric("Entregues", entregues_geral)
            col3.metric("Pendentes", pendentes_geral)
            col4.metric("% Concluído", f"{perc_geral:.1f}%")
        else:
            st.info("Nenhum dado disponível.")


# =====================================================
# MAIN
# =====================================================

def main():
    # Inicializa session_state
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    
    if "gs_client" not in st.session_state:
        st.session_state.gs_client = conectar_google_sheets()
    
    # Verifica login
    if st.session_state.usuario is None:
        tela_login()
    else:
        tela_principal()


if __name__ == "__main__":
    main()