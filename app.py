from flask import Flask, render_template, request, redirect, url_for
import os
from datetime import datetime
from urllib.parse import quote
from pymongo import MongoClient
from bson.objectid import ObjectId
import sys

app = Flask(__name__)

# Configuração do MongoDB
try:
    client = MongoClient('mongodb+srv://daniellucas89742:Al042318@cluster0.mpagchn.mongodb.net/')
    # Testa a conexão
    client.server_info()
    print("Conexão com MongoDB estabelecida com sucesso!")
    
    # Cria o banco de dados e a coleção se não existirem
    db = client['barbearia']
    if 'agendamentos' not in db.list_collection_names():
        db.create_collection('agendamentos')
        print("Coleção 'agendamentos' criada com sucesso!")
    
    agendamentos = db.agendamentos
except Exception as e:
    print(f"Erro ao conectar com MongoDB: {e}")
    sys.exit(1)

def validar_horario_funcionamento(data_str, hora_str):
    try:
        # Converte a string de data para objeto datetime
        data = datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M")
        
        # Verifica o dia da semana (0 = Domingo, 1 = Segunda, ..., 6 = Sábado)
        dia_semana = data.weekday()
        
        # Segunda-feira = 0, então não permitimos agendamentos
        if dia_semana == 0:  # Segunda-feira
            return False, "Não atendemos às segundas-feiras"
        
        # Converte a hora para número
        hora = int(hora_str.split(":")[0])
        minuto = int(hora_str.split(":")[1])
        
        # Verifica horário de funcionamento (9h às 19h)
        if hora < 9 or (hora == 19 and minuto > 0) or hora > 19:
            return False, "Horário de atendimento: 09:00 às 19:00"
            
        return True, "Horário válido"
    except ValueError:
        return False, "Data ou hora inválida"

def formatar_data(data_str):
    data = datetime.strptime(data_str, "%Y-%m-%d")
    return data.strftime("%d/%m")

def enviar_whatsapp(nome, telefone, data, hora):
    # Número do WhatsApp da barbearia
    numero_barbearia = "82988123197"
    
    # Remove caracteres não numéricos dos telefones
    telefone_cliente = ''.join(filter(str.isdigit, telefone))
    telefone_barbearia = ''.join(filter(str.isdigit, numero_barbearia))
    
    # Formata a mensagem de notificação para o dono
    mensagem_notificacao = f"*NOVO AGENDAMENTO*\n\nCliente: {nome}\nTelefone: {telefone}\nData: {data}\nHora: {hora}"
    
    # Formata a mensagem de confirmação para o cliente
    mensagem_cliente = f"Olá {nome}! Seu agendamento na *Barbearia Biu 1* foi confirmado para:\n\n📅 Data: {data}\n⏰ Hora: {hora}\n\nObrigado por escolher nossos serviços! 🎉"
    
    # Codifica as mensagens para URL
    mensagem_notificacao_encoded = quote(mensagem_notificacao)
    mensagem_cliente_encoded = quote(mensagem_cliente)
    
    # Cria os links do WhatsApp
    link_notificacao = f"https://wa.me/55{telefone_barbearia}?text={mensagem_notificacao_encoded}"
    link_cliente = f"https://wa.me/55{telefone_cliente}?text={mensagem_cliente_encoded}"
    
    print(f"Link para enviar notificação: {link_notificacao}")
    print(f"Link para enviar confirmação: {link_cliente}")
    
    # Retorna ambos os links
    return link_notificacao, link_cliente

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/agendar", methods=["POST"])
def agendar():
    nome = request.form["nome"].strip()
    telefone = request.form["telefone"].strip()
    data = request.form["data"].strip()
    hora = request.form["hora"].strip()

    if not nome or not telefone or not data or not hora:
        return "Por favor, preencha todos os campos.", 400

    # Valida horário de funcionamento
    valido, mensagem = validar_horario_funcionamento(data, hora)
    if not valido:
        return mensagem, 400

    # Formata a data para dia/mês
    data_formatada = formatar_data(data)

    novo_agendamento = {
        "nome": nome,
        "telefone": telefone,
        "data": data_formatada,
        "hora": hora,
        "data_completa": f"{data} {hora}"
    }

    try:
        # Salva no MongoDB
        result = agendamentos.insert_one(novo_agendamento)
        print(f"Agendamento salvo com ID: {result.inserted_id}")
    except Exception as e:
        print(f"Erro ao salvar no MongoDB: {e}")
        return "Erro ao salvar agendamento. Por favor, tente novamente.", 500
    
    link_notificacao, link_cliente = enviar_whatsapp(nome, telefone, data_formatada, hora)
    
    return redirect(link_notificacao)

@app.route("/agendamentos")
def listar_agendamentos():
    try:
        # Busca todos os agendamentos ordenados por data e hora
        todos_agendamentos = list(agendamentos.find().sort("data_completa", 1))
        print(f"Total de agendamentos encontrados: {len(todos_agendamentos)}")
        return render_template("agendamentos.html", agendamentos=todos_agendamentos)
    except Exception as e:
        print(f"Erro ao buscar agendamentos: {e}")
        return "Erro ao buscar agendamentos. Por favor, tente novamente.", 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
