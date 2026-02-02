import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import hashlib

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
# FUNÇÕES DO GOOGLE SHEETS
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
    """Cria as abas necessárias se não existirem"""
    if not client:
        return None
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        
        # Aba de Casas
        try:
            ws_casas = sheet.worksheet("Casas")
        except:
            ws_casas = sheet.add_worksheet(title="Casas", rows=1000, cols=10)
            ws_casas.update('A1', [["Município", "Casa", "Data Cadastro", "Cadastrado Por"]])
        
        # Aba de Entregas
        try:
            ws_entregas = sheet.worksheet("Entregas")
        except:
            ws_entregas = sheet.add_worksheet(title="Entregas", rows=5000, cols=10)
            ws_entregas.update('A1', [["Município", "Casa", "Material", "Entregue", "Data Entrega", "Confirmado Por"]])
        
        return sheet
    except Exception as e:
        st.error(f"Erro ao inicializar planilha: {e}")
        return None


def adicionar_casa(client, municipio, casa, usuario):
    """Adiciona uma nova casa na planilha"""
    if not client:
        return False, "Cliente do Google Sheets não inicializado"
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        
        # Garante que as abas existem
        try:
            ws_casas = sheet.worksheet("Casas")
        except:
            ws_casas = sheet.add_worksheet(title="Casas", rows=1000, cols=10)
            ws_casas.update('A1', [["Município", "Casa", "Data Cadastro", "Cadastrado Por"]])
        
        try:
            ws_entregas = sheet.worksheet("Entregas")
        except:
            ws_entregas = sheet.add_worksheet(title="Entregas", rows=5000, cols=10)
            ws_entregas.update('A1', [["Município", "Casa", "Material", "Entregue", "Data Entrega", "Confirmado Por"]])
        
        # Verifica se a casa já existe
        todas_casas = ws_casas.get_all_values()
        if len(todas_casas) > 1:  # Se tem mais que só o cabeçalho
            for linha in todas_casas[1:]:
                if len(linha) >= 2:
                    if linha[0].strip().lower() == municipio.strip().lower() and linha[1].strip().lower() == casa.strip().lower():
                        return False, "Casa já cadastrada neste município!"
        
        # Adiciona a casa
        data_cadastro = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ws_casas.append_row([municipio, casa, data_cadastro, usuario])
        
        # Adiciona os materiais padrão para esta casa
        for material in MATERIAIS_PADRAO:
            ws_entregas.append_row([municipio, casa, material, "Não", "", ""])
        
        return True, f"✅ Casa '{casa}' adicionada com sucesso em {municipio}!"
    except Exception as e:
        import traceback
        erro_completo = traceback.format_exc()
        return False, f"Erro ao adicionar casa: {str(e)}\n\nDetalhes: {erro_completo}"


def carregar_casas(client):
    """Carrega todas as casas cadastradas"""
    if not client:
        return {}
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_casas = sheet.worksheet("Casas")
        
        dados = ws_casas.get_all_values()[1:]  # Pula cabeçalho
        
        casas_por_municipio = {}
        for linha in dados:
            if len(linha) >= 2:
                municipio = linha[0]
                casa = linha[1]
                
                if municipio not in casas_por_municipio:
                    casas_por_municipio[municipio] = []
                
                if casa not in casas_por_municipio[municipio]:
                    casas_por_municipio[municipio].append(casa)
        
        return casas_por_municipio
    except Exception as e:
        st.error(f"Erro ao carregar casas: {e}")
        return {}


def carregar_entregas(client, municipio, casa):
    """Carrega as entregas de uma casa específica"""
    if not client:
        return []
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_entregas = sheet.worksheet("Entregas")
        
        todos_dados = ws_entregas.get_all_values()
        
        entregas = []
        for i, linha in enumerate(todos_dados[1:], start=2):  # Pula cabeçalho, começa da linha 2
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
    except Exception as e:
        st.error(f"Erro ao carregar entregas: {e}")
        return []


def marcar_entrega(client, linha, material, usuario):
    """Marca um material como entregue"""
    if not client:
        return False, "Cliente do Google Sheets não inicializado"
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_entregas = sheet.worksheet("Entregas")
        
        data_entrega = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Atualiza a linha específica (colunas D, E, F)
        ws_entregas.update(f'D{linha}:F{linha}', [["Sim", data_entrega, usuario]])
        
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
        
        # Atualiza a linha específica (colunas D, E, F)
        ws_entregas.update(f'D{linha}:F{linha}', [["Não", "", ""]])
        
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
    
    # MUDANÇA IMPORTANTE: Mesmo se houver erro, mostra as tabs
    erro_conexao = False
    if not client:
        st.error("❌ Erro ao conectar com Google Sheets. Verifique as credenciais no Secrets.")
        erro_conexao = True
    
    # Tenta inicializar a planilha
    sheet_result = None
    if client:
        with st.spinner("Conectando à planilha..."):
            sheet_result = inicializar_planilha(client)
            if not sheet_result:
                st.error("❌ Erro ao acessar a planilha. Verifique as permissões.")
                erro_conexao = True
    
    # Tabs - SEMPRE MOSTRADAS
    tab1, tab2, tab3 = st.tabs(["📋 Controle de Entregas", "🏠 Adicionar Casa", "📊 Relatório"])
    
    # Se houver erro de conexão, mostra mensagem em todas as tabs
    if erro_conexao:
        with tab1:
            st.warning("⚠️ Não é possível acessar os dados. Verifique a conexão com o Google Sheets.")
            st.info("👉 Vá em 'Manage app' → 'Settings' → 'Secrets' e configure corretamente.")
        
        with tab2:
            st.warning("⚠️ Não é possível adicionar casas. Verifique a conexão com o Google Sheets.")
            st.info("👉 Vá em 'Manage app' → 'Settings' → 'Secrets' e configure corretamente.")
        
        with tab3:
            st.warning("⚠️ Não é possível gerar relatórios. Verifique a conexão com o Google Sheets.")
        
        return
    
    # ===== TAB 1: CONTROLE DE ENTREGAS =====
    with tab1:
        st.subheader("Controle de Entregas")
        
        casas_por_municipio = carregar_casas(client)
        
        if not casas_por_municipio:
            st.info("Nenhuma casa cadastrada ainda. Adicione casas na aba 'Adicionar Casa'.")
        else:
            # Seleção de município
            municipio_selecionado = st.selectbox("Selecione o Município", MUNICIPIOS)
            
            if municipio_selecionado in casas_por_municipio:
                casas = casas_por_municipio[municipio_selecionado]
                
                # Exibe cada casa
                for casa in casas:
                    with st.expander(f"🏠 {casa}", expanded=True):
                        entregas = carregar_entregas(client, municipio_selecionado, casa)
                        
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
                                # Checkbox para marcar/desmarcar
                                chave = f"check_{municipio_selecionado}_{casa}_{item['linha']}"
                                
                                if st.checkbox(
                                    "✅" if item["entregue"] else "❌",
                                    value=item["entregue"],
                                    key=chave,
                                    label_visibility="collapsed"
                                ):
                                    if not item["entregue"]:
                                        # Marcar como entregue
                                        sucesso, msg = marcar_entrega(
                                            client, 
                                            item["linha"], 
                                            item["material"], 
                                            st.session_state.nome_usuario
                                        )
                                        if sucesso:
                                            st.rerun()
                                else:
                                    if item["entregue"]:
                                        # Desmarcar
                                        sucesso, msg = desmarcar_entrega(client, item["linha"])
                                        if sucesso:
                                            st.rerun()
                            
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
                st.error("❌ Por favor, digite o nome da casa!")
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
                        st.info("🔄 Recarregando dados...")
                        # Limpa o cache para forçar reload
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.error(msg)
        
        # Mostra as casas já cadastradas
        st.markdown("---")
        st.subheader("📋 Casas Cadastradas")
        
        casas_cadastradas = carregar_casas(client)
        
        if casas_cadastradas:
            for mun in MUNICIPIOS:
                if mun in casas_cadastradas and casas_cadastradas[mun]:
                    with st.expander(f"📍 {mun} ({len(casas_cadastradas[mun])} casas)"):
                        for idx, casa_nome in enumerate(casas_cadastradas[mun], 1):
                            st.write(f"{idx}. {casa_nome}")
        else:
            st.info("Nenhuma casa cadastrada ainda.")
    
    # ===== TAB 3: RELATÓRIO =====
    with tab3:
        st.subheader("Relatório de Entregas")
        
        casas_por_municipio = carregar_casas(client)
        
        if not casas_por_municipio:
            st.info("Nenhum dado disponível.")
            return
        
        # Dados para o relatório
        dados_relatorio = []
        
        for municipio in MUNICIPIOS:
            if municipio in casas_por_municipio:
                for casa in casas_por_municipio[municipio]:
                    entregas = carregar_entregas(client, municipio, casa)
                    
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