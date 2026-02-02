import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import gspread
from google.oauth2.service_account import Credentials
import hashlib

# Configuração da página
st.set_page_config(
    page_title="Controle de Entregas - Obra",
    page_icon="🏗️",
    layout="wide"
)

# Arquivos para persistir dados
DATA_FILE = "entregas_obra.json"
USERS_FILE = "usuarios.json"

# ==========================================
# 🗺️ CONFIGURAÇÃO DE MUNICÍPIOS
# ==========================================
# ADICIONE OU REMOVA MUNICÍPIOS AQUI!

MUNICIPIOS = [
    "São Vicente do Seridó",
    "Pedra Lavrada",
    # ADICIONE MAIS MUNICÍPIOS ABAIXO:
    # "Nome do Município",
]

# ==========================================
# 🔧 CONFIGURAÇÃO DE MATERIAIS
# ==========================================
# ADICIONE OU REMOVA MATERIAIS AQUI!
# Cada material pode ter: nome, quantidade padrão (opcional)

MATERIAIS_PADRAO = [
    {"nome": "Tijolo", "quantidade_padrao": "1000 un"},
    {"nome": "Brita", "quantidade_padrao": "5 m³"},
    {"nome": "Areia", "quantidade_padrao": "5 m³"},
    {"nome": "Cimento", "quantidade_padrao": "50 sacos"},
    {"nome": "Ferro 8mm", "quantidade_padrao": "100 barras"},
    {"nome": "Ferro 10mm", "quantidade_padrao": "80 barras"},
    {"nome": "Tubo PVC 100mm", "quantidade_padrao": "20 metros"},
    {"nome": "Tubo PVC 50mm", "quantidade_padrao": "30 metros"},
    {"nome": "Fio 2,5mm", "quantidade_padrao": "2 rolos"},
    {"nome": "Fio 4mm", "quantidade_padrao": "1 rolo"},
    # ADICIONE MAIS MATERIAIS ABAIXO:
    # {"nome": "Nome do Material", "quantidade_padrao": "X unidades"},
]

# ==========================================
# 👥 CONFIGURAÇÃO DE USUÁRIOS
# ==========================================
# ADICIONE OU REMOVA USUÁRIOS AQUI!
# Formato: {"username": "login", "nome": "Nome Completo", "pin": "0000", "admin": True/False}

USUARIOS_PADRAO = [
    {"username": "gutemberg", "nome": "Gutemberg Martins", "pin": "0000", "admin": True},
    {"username": "severino", "nome": "Severino Cordeiro", "pin": "0101", "admin": False},
    {"username": "virgilho", "nome": "Virgilho Cordeiro", "pin": "0209", "admin": False},
    {"username": "gutemberg_filho", "nome": "Gutemberg Filho", "pin": "2004", "admin": False},
    # ADICIONE MAIS USUÁRIOS ABAIXO:
    # {"username": "login", "nome": "Nome Completo", "pin": "1234", "admin": False},
]

# ==========================================

# Configuração do Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# ==========================================
# FUNÇÕES DE USUÁRIO
# ==========================================

def carregar_usuarios():
    """Carrega usuários do arquivo JSON ou inicializa com usuários padrão"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Inicializar com usuários padrão do código
    usuarios = {}
    for user in USUARIOS_PADRAO:
        usuarios[user["username"]] = {
            "nome": user["nome"],
            "pin_hash": hash_pin(user["pin"]),
            "admin": user.get("admin", False)
        }
    
    # Salvar no arquivo
    salvar_usuarios(usuarios)
    return usuarios

def salvar_usuarios(usuarios):
    """Salva usuários no arquivo JSON"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)

def hash_pin(pin):
    """Cria hash do PIN"""
    return hashlib.sha256(pin.encode()).hexdigest()

def verificar_pin(username, pin, usuarios):
    """Verifica se o PIN está correto"""
    if username in usuarios:
        return usuarios[username]["pin_hash"] == hash_pin(pin)
    return False

# ==========================================
# FUNÇÕES DO GOOGLE SHEETS
# ==========================================

def conectar_google_sheets():
    """Conecta ao Google Sheets usando credenciais do Streamlit Secrets"""
    try:
        if "gcp_service_account" in st.secrets:
            credentials = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
            client = gspread.authorize(credentials)
            return client
        return None
    except Exception as e:
        st.sidebar.error(f"Erro ao conectar Google Sheets: {str(e)}")
        return None

def sincronizar_sheets(dados, client, sheet_url):
    """Envia dados para o Google Sheets"""
    try:
        sheet = client.open_by_url(sheet_url)
        
        # Preparar dados para exportar
        rows = []
        rows.append(["Município", "Casa", "Material", "Quantidade", "Data Prevista", "Status", "Data Entrega", "Confirmado Por"])
        
        for municipio, casas in dados["municipios"].items():
            for casa, materiais in casas.items():
                for item in materiais:
                    rows.append([
                        municipio,
                        casa,
                        item["material"],
                        item.get("quantidade", ""),
                        item.get("data_prevista", ""),
                        "✅ Entregue" if item["entregue"] else "⏳ Pendente",
                        item.get("data_entrega", ""),
                        item.get("confirmado_por", "")
                    ])
        
        # Atualizar worksheet
        try:
            worksheet = sheet.worksheet("Controle de Entregas")
        except:
            worksheet = sheet.add_worksheet(title="Controle de Entregas", rows=100, cols=10)
        
        worksheet.clear()
        worksheet.update('A1', rows)
        
        return True
    except Exception as e:
        st.sidebar.error(f"Erro ao sincronizar: {str(e)}")
        return False

def carregar_sheets(client, sheet_url):
    """Carrega dados do Google Sheets"""
    try:
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.worksheet("Controle de Entregas")
        data = worksheet.get_all_values()
        
        if len(data) <= 1:
            return {"municipios": {}}
        
        dados = {"municipios": {}}
        
        for row in data[1:]:
            if len(row) < 7:
                continue
                
            municipio = row[0]
            casa = row[1]
            
            if municipio not in dados["municipios"]:
                dados["municipios"][municipio] = {}
            
            if casa not in dados["municipios"][municipio]:
                dados["municipios"][municipio][casa] = []
            
            item = {
                "material": row[2],
                "quantidade": row[3],
                "data_prevista": row[4] if row[4] else None,
                "entregue": row[5] == "✅ Entregue",
                "data_entrega": row[6] if row[6] else None,
                "confirmado_por": row[7] if len(row) > 7 and row[7] else None
            }
            dados["municipios"][municipio][casa].append(item)
        
        return dados
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar do Sheets: {str(e)}")
        return {"municipios": {}}

# ==========================================
# FUNÇÕES DE DADOS
# ==========================================

def carregar_dados():
    """Carrega dados do arquivo JSON local"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Migração de estrutura antiga (casas) para nova (municipios)
            if "casas" in data and "municipios" not in data:
                # Converter formato antigo
                data["municipios"] = {"Sem Município": data["casas"]}
                del data["casas"]
                salvar_dados(data)
            return data
    return {"municipios": {}}

def salvar_dados(dados):
    """Salva dados no arquivo JSON local"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def inicializar_materiais_casa():
    """Cria checklist inicial de materiais para uma nova casa"""
    materiais = []
    for mat in MATERIAIS_PADRAO:
        materiais.append({
            "material": mat["nome"],
            "quantidade": mat.get("quantidade_padrao", ""),
            "data_prevista": None,
            "entregue": False,
            "data_entrega": None,
            "confirmado_por": None
        })
    return materiais

# ==========================================
# FUNÇÕES DE RENDERIZAÇÃO
# ==========================================

def renderizar_checklist(municipio, nome_casa, materiais, usuario_logado):
    """Renderiza o checklist de materiais para uma casa"""
    
    # Estatísticas da casa
    total = len(materiais)
    entregues = sum(1 for item in materiais if item["entregue"])
    pendentes = total - entregues
    percentual = int((entregues / total * 100)) if total > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", total)
    with col2:
        st.metric("✅ Entregues", entregues)
    with col3:
        st.metric("⏳ Pendentes", pendentes)
    with col4:
        st.metric("Progresso", f"{percentual}%")
    
    # Barra de progresso
    st.progress(percentual / 100)
    
    st.markdown("---")
    
    # Checklist de materiais
    st.subheader("📋 Checklist de Materiais")
    
    # Separar pendentes e entregues
    pendentes_lista = [item for item in materiais if not item["entregue"]]
    entregues_lista = [item for item in materiais if item["entregue"]]
    
    # Mostrar pendentes
    if pendentes_lista:
        st.markdown("**⏳ Pendentes:**")
        for idx, item in enumerate(pendentes_lista):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.markdown(f"**{item['material']}**")
            with col2:
                # Permitir editar quantidade
                nova_qtd = st.text_input(
                    "Quantidade",
                    value=item.get("quantidade", ""),
                    key=f"qtd_{municipio}_{nome_casa}_{item['material']}_pend",
                    label_visibility="collapsed",
                    placeholder="Ex: 1000 un"
                )
                if nova_qtd != item.get("quantidade", ""):
                    item["quantidade"] = nova_qtd
                    salvar_dados(st.session_state.dados)
            
            with col3:
                # Permitir editar data prevista
                data_atual = None
                if item.get("data_prevista"):
                    try:
                        data_atual = datetime.strptime(item["data_prevista"], "%d/%m/%Y")
                    except:
                        pass
                
                nova_data = st.date_input(
                    "Data prevista",
                    value=data_atual,
                    key=f"data_{municipio}_{nome_casa}_{item['material']}_pend",
                    label_visibility="collapsed",
                    format="DD/MM/YYYY"
                )
                
                if nova_data:
                    nova_data_str = nova_data.strftime("%d/%m/%Y")
                    if nova_data_str != item.get("data_prevista"):
                        item["data_prevista"] = nova_data_str
                        salvar_dados(st.session_state.dados)
            
            with col4:
                if st.button("✓", key=f"check_{municipio}_{nome_casa}_{item['material']}", help="Marcar como entregue"):
                    item["entregue"] = True
                    item["data_entrega"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    item["confirmado_por"] = usuario_logado
                    salvar_dados(st.session_state.dados)
                    st.rerun()
    
    # Mostrar entregues
    if entregues_lista:
        st.markdown("---")
        with st.expander(f"✅ Materiais Entregues ({len(entregues_lista)})", expanded=False):
            for item in entregues_lista:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.markdown(f"~~{item['material']}~~")
                with col2:
                    if item.get('quantidade'):
                        st.text(f"Qtd: {item['quantidade']}")
                with col3:
                    if item.get('data_entrega'):
                        st.text(f"Entregue: {item['data_entrega']}")
                    if item.get('confirmado_por'):
                        st.caption(f"👤 Por: {item['confirmado_por']}")
                with col4:
                    if st.button("↻", key=f"uncheck_{municipio}_{nome_casa}_{item['material']}", help="Desmarcar"):
                        item["entregue"] = False
                        item["data_entrega"] = None
                        item["confirmado_por"] = None
                        salvar_dados(st.session_state.dados)
                        st.rerun()

# ==========================================
# TELA DE LOGIN
# ==========================================

def tela_login():
    """Renderiza tela de login"""
    st.title("🔐 Login - Controle de Entregas")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        
        usuarios = carregar_usuarios()
        
        # Selecionar usuário
        username = st.selectbox(
            "Selecione seu usuário",
            options=list(usuarios.keys()),
            format_func=lambda x: f"{usuarios[x]['nome']} ({x})"
        )
        
        # PIN
        pin = st.text_input(
            "Digite seu PIN (4 dígitos)",
            type="password",
            max_chars=4,
            help="Digite seu PIN de 4 dígitos"
        )
        
        if st.button("🔓 Entrar", type="primary", use_container_width=True):
            if verificar_pin(username, pin, usuarios):
                st.session_state.usuario_logado = username
                st.session_state.nome_usuario = usuarios[username]["nome"]
                st.session_state.is_admin = usuarios[username].get("admin", False)
                st.success(f"Bem-vindo, {usuarios[username]['nome']}!")
                st.rerun()
            else:
                st.error("❌ PIN incorreto!")
        
        st.markdown("---")

# ==========================================
# INICIALIZAÇÃO
# ==========================================

# Inicializar session state
if 'dados' not in st.session_state:
    st.session_state.dados = carregar_dados()

if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None

# ==========================================
# ROTEAMENTO DE TELAS
# ==========================================

# Se não estiver logado, mostrar tela de login
if not st.session_state.usuario_logado:
    tela_login()
# Se estiver logado, mostrar aplicação principal
else:
    # ==========================================
    # APLICAÇÃO PRINCIPAL
    # ==========================================
    
    # Título com informação do usuário
    col_title, col_user = st.columns([3, 1])
    with col_title:
        st.title("🏗️ Controle de Entregas de Materiais")
    with col_user:
        st.markdown(f"**👤 {st.session_state.nome_usuario}**")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.usuario_logado = None
            st.session_state.nome_usuario = None
            st.session_state.is_admin = None
            st.rerun()
    
    st.markdown("---")
    
    # ==========================================
    # SIDEBAR
    # ==========================================
    
    with st.sidebar:
        st.header("☁️ Google Sheets")
        
        usar_sheets = st.checkbox("Usar Google Sheets", value=False)
        
        if usar_sheets:
            sheet_url = st.text_input(
                "URL da Planilha Google",
                placeholder="https://docs.google.com/spreadsheets/d/...",
                help="Cole a URL completa da sua planilha"
            )
            
            if sheet_url:
                client = conectar_google_sheets()
                
                if client:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📥 Carregar", help="Carregar dados do Sheets"):
                            dados_sheets = carregar_sheets(client, sheet_url)
                            if dados_sheets:
                                st.session_state.dados = dados_sheets
                                salvar_dados(st.session_state.dados)
                                st.success("Dados carregados!")
                                st.rerun()
                    
                    with col2:
                        if st.button("📤 Sincronizar", help="Enviar dados para o Sheets"):
                            if sincronizar_sheets(st.session_state.dados, client, sheet_url):
                                st.success("Sincronizado!")
                else:
                    st.warning("⚠️ Configure as credenciais nos Secrets")
        
        st.markdown("---")
        
        st.header("🏠 Adicionar Casa")
        
        # Selecionar município
        municipio_selecionado = st.selectbox(
            "Município",
            options=MUNICIPIOS,
            help="Selecione o município da casa"
        )
        
        nova_casa = st.text_input("Nome da Casa", placeholder="Ex: Casa X, Casa Y, Lote 15...")
        
        if st.button("➕ Adicionar Casa", type="primary"):
            if nova_casa:
                # Inicializar município se não existir
                if municipio_selecionado not in st.session_state.dados["municipios"]:
                    st.session_state.dados["municipios"][municipio_selecionado] = {}
                
                # Verificar se casa já existe neste município
                if nova_casa in st.session_state.dados["municipios"][municipio_selecionado]:
                    st.error(f"Esta casa já existe em {municipio_selecionado}!")
                else:
                    # Inicializar com checklist padrão de materiais
                    st.session_state.dados["municipios"][municipio_selecionado][nova_casa] = inicializar_materiais_casa()
                    salvar_dados(st.session_state.dados)
                    st.success(f"✅ {nova_casa} adicionada em {municipio_selecionado}!")
                    st.rerun()
            else:
                st.error("Digite o nome da casa")
        
        st.markdown("---")
        
        # Opções de gerenciamento
        if st.session_state.dados["municipios"]:
            st.header("🗑️ Gerenciar")
            
            # Selecionar município para gerenciar
            municipios_com_casas = [m for m in st.session_state.dados["municipios"].keys() if st.session_state.dados["municipios"][m]]
            
            if municipios_com_casas:
                municipio_gerenciar = st.selectbox(
                    "Município",
                    options=municipios_com_casas,
                    key="mun_gerenciar"
                )
                
                casa_gerenciar = st.selectbox(
                    "Casa",
                    options=list(st.session_state.dados["municipios"][municipio_gerenciar].keys()),
                    key="casa_gerenciar"
                )
                
                if st.button("🔄 Resetar Entregas", help="Desmarca todos os itens como não entregues"):
                    for item in st.session_state.dados["municipios"][municipio_gerenciar][casa_gerenciar]:
                        item["entregue"] = False
                        item["data_entrega"] = None
                        item["confirmado_por"] = None
                    salvar_dados(st.session_state.dados)
                    st.success(f"Entregas de {casa_gerenciar} resetadas!")
                    st.rerun()
                
                if st.session_state.is_admin:
                    if st.button("⚠️ Remover Casa", type="secondary"):
                        del st.session_state.dados["municipios"][municipio_gerenciar][casa_gerenciar]
                        # Remover município se ficar vazio
                        if not st.session_state.dados["municipios"][municipio_gerenciar]:
                            del st.session_state.dados["municipios"][municipio_gerenciar]
                        salvar_dados(st.session_state.dados)
                        st.success(f"{casa_gerenciar} removida!")
                        st.rerun()
        
        st.markdown("---")
        
        # Informação sobre usuários (apenas para admin)
        if st.session_state.is_admin:
            st.header("👥 Usuários")
            usuarios = carregar_usuarios()
            st.info(f"**{len(usuarios)} usuários cadastrados**\n\nPara adicionar/remover usuários, edite a seção CONFIGURAÇÃO DE USUÁRIOS no código.")
            
            st.markdown("---")
        
        st.info(f"🗺️ Municípios: **{len(MUNICIPIOS)}**")
        st.info(f"📦 Materiais: **{len(MATERIAIS_PADRAO)}**")
        st.caption("💡 Edite o código para adicionar/remover municípios, materiais ou usuários")
    
    # ==========================================
    # ÁREA PRINCIPAL
    # ==========================================
    
    municipios = st.session_state.dados["municipios"]
    
    if not municipios or not any(municipios.values()):
        st.info("🏠 Nenhuma casa cadastrada. Adicione casas usando o menu lateral.")
        st.markdown("### 🗺️ Municípios disponíveis:")
        for mun in MUNICIPIOS:
            st.markdown(f"- {mun}")
        st.markdown("### 📋 Materiais que serão incluídos automaticamente:")
        for mat in MATERIAIS_PADRAO:
            st.markdown(f"- **{mat['nome']}** ({mat.get('quantidade_padrao', 'Sem quantidade padrão')})")
    else:
        # Estatísticas gerais
        total_municipios = len([m for m in municipios.keys() if municipios[m]])
        total_casas = sum(len(casas) for casas in municipios.values())
        total_checks = sum(len(materiais) for casas in municipios.values() for materiais in casas.values())
        total_entregues = sum(
            sum(1 for item in materiais if item["entregue"]) 
            for casas in municipios.values() 
            for materiais in casas.values()
        )
        percentual = int((total_entregues / total_checks * 100)) if total_checks > 0 else 0
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("🗺️ Municípios", total_municipios)
        with col2:
            st.metric("🏠 Casas", total_casas)
        with col3:
            st.metric("📦 Checks", total_checks)
        with col4:
            st.metric("✅ Entregues", total_entregues)
        with col5:
            st.metric("📊 Progresso", f"{percentual}%")
        
        st.markdown("---")
        
        # Criar tabs por município
        municipios_com_casas = {m: casas for m, casas in municipios.items() if casas}
        
        if municipios_com_casas:
            tabs_municipios = st.tabs([f"🗺️ {mun}" for mun in municipios_com_casas.keys()])
            
            for tab_mun, (municipio, casas) in zip(tabs_municipios, municipios_com_casas.items()):
                with tab_mun:
                    # Estatísticas do município
                    total_casas_mun = len(casas)
                    total_materiais_mun = sum(len(materiais) for materiais in casas.values())
                    entregues_mun = sum(
                        sum(1 for item in materiais if item["entregue"]) 
                        for materiais in casas.values()
                    )
                    percentual_mun = int((entregues_mun / total_materiais_mun * 100)) if total_materiais_mun > 0 else 0
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🏠 Casas", total_casas_mun)
                    with col2:
                        st.metric("📦 Total Checks", total_materiais_mun)
                    with col3:
                        st.metric("✅ Entregues", entregues_mun)
                    with col4:
                        st.metric("📊 Progresso", f"{percentual_mun}%")
                    
                    st.progress(percentual_mun / 100)
                    st.markdown("---")
                    
                    # Mostrar casas deste município
                    if len(casas) == 1:
                        # Se for apenas uma casa, renderizar diretamente
                        nome_casa = list(casas.keys())[0]
                        materiais = casas[nome_casa]
                        st.subheader(f"🏠 {nome_casa}")
                        renderizar_checklist(municipio, nome_casa, materiais, st.session_state.nome_usuario)
                    else:
                        # Múltiplas casas - criar tabs
                        tabs_casas = st.tabs([f"🏠 {nome}" for nome in casas.keys()])
                        
                        for tab_casa, (nome_casa, materiais) in zip(tabs_casas, casas.items()):
                            with tab_casa:
                                renderizar_checklist(municipio, nome_casa, materiais, st.session_state.nome_usuario)
    
    # Rodapé
    st.markdown("---")
    st.caption("💡 Dica: Casas são agrupadas por município para facilitar a logística de entrega!")
    st.caption("🔧 Edite o código nas seções de CONFIGURAÇÃO para personalizar municípios, materiais e usuários.")