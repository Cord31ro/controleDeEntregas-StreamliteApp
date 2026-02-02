# 🏗️ Sistema de Controle de Entregas de Materiais

Sistema web com **checklist automático**, **controle de usuários** e **registro de quem confirmou cada entrega**.

## 💡 Como Funciona

**Conceito simples:** Todas as casas levam os mesmos materiais! 

Ao invés de ficar adicionando material por material, você:
1. **Faz login** com seu usuário e PIN de 4 dígitos
2. **Configura UMA VEZ** a lista de materiais no código
3. **Adiciona casas** - cada casa já vem com o checklist completo
4. **Marca entregas** - fica registrado quem confirmou

## 📋 Funcionalidades

- 🔐 **Sistema de login com PIN de 4 dígitos**
- 👤 **Registro de quem confirmou cada entrega**
- ✅ **Checklist automático** - Adiciona casa, já vem com todos os materiais
- ✅ **Lista de materiais editável** - Configure uma vez no código
- ✅ Quantidade padrão para cada material
- ✅ Data prevista de entrega editável por item
- ✅ Marcar/desmarcar entregas com um clique
- ✅ Visualização por abas (uma aba por casa)
- ✅ Progresso visual com métricas e barra
- ✅ Histórico de entregas com data/hora
- ✅ **Sincronização com Google Sheets** (inclui coluna "Confirmado Por")
- ✅ Resetar entregas de uma casa
- ✅ Dados salvos automaticamente
- 👥 **Gerenciamento de usuários** (para admin)

## 🔧 Como Adicionar/Remover Materiais

Edite a seção **CONFIGURAÇÃO DE MATERIAIS** no arquivo `controle_entregas.py`:

```python
# ==========================================
# 🔧 CONFIGURAÇÃO DE MATERIAIS
# ==========================================
MATERIAIS_PADRAO = [
    {"nome": "Tijolo", "quantidade_padrao": "1000 un"},
    {"nome": "Brita", "quantidade_padrao": "5 m³"},
    {"nome": "Areia", "quantidade_padrao": "5 m³"},
    {"nome": "Cimento", "quantidade_padrao": "50 sacos"},
    # ADICIONE MAIS MATERIAIS ABAIXO:
    {"nome": "Seu Material", "quantidade_padrao": "X unidades"},
]
```

**É FÁCIL:**
- Para adicionar: cole uma nova linha
- Para remover: delete a linha
- Para mudar quantidade: edite o número

**Veja o arquivo [GUIA_EDICAO_MATERIAIS.md](GUIA_EDICAO_MATERIAIS.md) para mais detalhes.**

## 👥 Como Adicionar/Remover Usuários

Edite a seção **CONFIGURAÇÃO DE USUÁRIOS** no arquivo `controle_entregas.py`:

```python
# ==========================================
# 👥 CONFIGURAÇÃO DE USUÁRIOS
# ==========================================
USUARIOS_PADRAO = [
    {"username": "gutemberg", "nome": "Gutemberg Martins", "pin": "0000", "admin": True},
    {"username": "severino", "nome": "Severino Cordeiro", "pin": "0101", "admin": False},
    # ADICIONE MAIS USUÁRIOS ABAIXO:
    {"username": "login", "nome": "Nome Completo", "pin": "1234", "admin": False},
]
```

**É FÁCIL:**
- Para adicionar: cole uma nova linha
- Para remover: delete a linha
- Para mudar PIN: edite os 4 dígitos

**Veja o arquivo [GUIA_USUARIOS.md](GUIA_USUARIOS.md) para mais detalhes.**

## 🚀 Como usar localmente

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Executar a aplicação

```bash
streamlit run controle_entregas.py
```

A aplicação abrirá automaticamente no navegador em `http://localhost:8501`

## 🌐 Como hospedar no Streamlit Cloud (GRÁTIS)

### 1. Criar conta no GitHub
- Acesse [github.com](https://github.com) e crie uma conta gratuita

### 2. Criar repositório
- Clique em "New repository"
- Dê um nome (ex: `controle-entregas-obra`)
- Marque como "Public"
- Clique em "Create repository"

### 3. Fazer upload dos arquivos
- Clique em "uploading an existing file"
- Arraste os arquivos: `controle_entregas.py` e `requirements.txt`
- Clique em "Commit changes"

### 4. Hospedar no Streamlit Cloud
- Acesse [share.streamlit.io](https://share.streamlit.io)
- Faça login com sua conta GitHub
- Clique em "New app"
- Selecione seu repositório
- Em "Main file path" coloque: `controle_entregas.py`
- Clique em "Deploy!"

Pronto! Seu app estará disponível em um link público que você pode acessar de qualquer lugar!

## 📱 Como usar o sistema

### Passo 0: Primeiro Acesso
1. Ao abrir o app, você verá a tela de login
2. Selecione seu usuário no dropdown
3. Digite seu PIN de 4 dígitos
4. Clique em "🔓 Entrar"

**Usuários disponíveis:**
- Gutemberg Martins (gutemberg) - Admin
- Severino Cordeiro (severino)
- Virgilho Cordeiro (virgilho)
- Gutemberg Filho (gutemberg_filho)

### Passo 1: Configurar Usuários (se necessário)
1. Abra o arquivo `controle_entregas.py`
2. Encontre a seção `CONFIGURAÇÃO DE USUÁRIOS`
3. Adicione, remova ou edite usuários conforme necessário
4. Salve o arquivo e reinicie o app

### Passo 2: Configurar Lista de Materiais (UMA VEZ)
1. Abra o arquivo `controle_entregas.py`
2. Encontre a seção `CONFIGURAÇÃO DE MATERIAIS`
3. Adicione/remova/edite os materiais conforme necessário
4. Salve o arquivo

### Passo 3: Adicionar Casas
1. Faça login com seu usuário
2. No menu lateral, digite o nome da casa (ex: "Casa X", "Lote 15")
3. Clique em "➕ Adicionar Casa"
4. **Pronto!** A casa já vem com checklist completo de materiais

### Passo 4: Usar o Checklist
1. Selecione a aba da casa (se tiver múltiplas)
2. Edite quantidade ou data prevista se necessário
3. Clique no ✓ quando o material for entregue
4. **Fica registrado:** Seu nome aparecerá como quem confirmou a entrega!
5. Veja o progresso em tempo real!

### Passo 5: Sincronizar com Google Sheets (Opcional)
1. Configure seguindo o [GUIA_GOOGLE_SHEETS.md](GUIA_GOOGLE_SHEETS.md)
2. Marque "Usar Google Sheets" no menu lateral
3. Cole a URL da sua planilha
4. Clique em "📤 Sincronizar"
5. A planilha terá uma coluna "Confirmado Por" mostrando quem marcou cada entrega

### Passo 6: Gerenciar
- **Resetar Entregas**: Desmarca tudo para recomeçar
- **Remover Casa**: Deleta a casa completa (apenas admin)

## ☁️ Google Sheets - Vantagens

Ao integrar com Google Sheets você tem:
- 📊 Dados na nuvem (não perde se o servidor reiniciar)
- 👥 Múltiplos usuários podem acessar
- 📱 Acesso direto pelo app do Google Sheets no celular
- 📈 Pode criar gráficos e relatórios personalizados
- 🔄 Sincronização bidirecional (edite na planilha ou no app)

## 💾 Persistência de Dados

### Modo LOCAL (sem Google Sheets):
- **Entregas:** Salvos em `entregas_obra.json`
- **Usuários:** Salvos em `usuarios.json`

### Modo GOOGLE SHEETS (recomendado para produção):
Os dados de entregas ficam na nuvem e são sincronizados com sua planilha Google (incluindo coluna "Confirmado Por").
Usuários ainda ficam salvos localmente no arquivo `usuarios.json`.

**IMPORTANTE**: Se hospedar no Streamlit Cloud SEM Google Sheets, os dados serão resetados quando o app reiniciar.

## 🔐 Segurança

- **Todos usam PIN de 4 dígitos** (incluindo admin)
- PINs são armazenados com hash SHA-256 (não são salvos em texto puro)
- Cada usuário tem seu próprio login e PIN
- Usuários são configurados diretamente no código
- Apenas administradores podem remover casas
- Todas as ações ficam registradas com nome do usuário
- **Recomendação:** Use PINs diferentes e seguros para cada usuário!

## 🔧 Melhorias futuras sugeridas

- [x] Integração com Google Sheets ✅
- [x] Data prevista de entrega ✅
- [x] Sistema de login para múltiplos usuários ✅
- [x] Registro de quem confirmou cada entrega ✅
- [ ] Relatórios e gráficos de entregas
- [ ] Notificações de materiais com entrega atrasada
- [ ] Exportar dados para Excel/PDF
- [ ] Upload de fotos dos materiais entregues
- [ ] Filtros e busca de materiais
- [ ] Histórico de alterações

## 📞 Suporte

Alguma dúvida ou sugestão? Edite o código livremente e adapte às suas necessidades!