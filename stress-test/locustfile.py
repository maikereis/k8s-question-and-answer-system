import random
from locust import HttpUser, task, between


# --- CLASSE 1: Comportamento de Usuário Comum ---
class PowerConsumerUser(HttpUser):
    # Tempo de espera entre as requisições (entre 1 e 5 segundos)
    wait_time = between(1, 5)

    questions = [
        "Quanto tempo a distribuidora tem para ligar a luz em um apartamento novo?",
        "Qual o prazo para ligação trifásica em área comercial urbana?",
        "Vou abrir uma indústria, qual o prazo máximo para ligação em alta tensão?",
        "Quais documentos preciso levar para pedir uma ligação nova?",
        "A distribuidora atrasou minha ligação nova, como posso reclamar?",
        "Posso pedir ligação de energia pelo site ou aplicativo?",
        "Existe diferença de prazo entre ligação monofásica e bifásica na cidade?",
        "Minha ligação nova está atrasada há 15 dias, tenho direito a compensação?",
        "A distribuidora pode cobrar taxa para fazer a primeira ligação?",
        "Moro no sítio, o prazo de ligação é o mesmo da cidade?",
        "Paguei a conta atrasada, em quanto tempo a energia volta na cidade?",
        "Moro na zona rural e paguei a conta hoje, quando religam minha luz?",
        "A taxa de religação por atraso no pagamento é obrigatória?",
        "Tenho um respirador em casa, a distribuidora pode cortar minha luz por dívida?",
        "O corte de energia por erro da empresa gera taxa de religação?",
        "A empresa de energia precisa avisar com quantos dias de antecedência sobre o corte?",
        "Sou eletrodependente e cortaram minha luz por engano, o que faço?",
        "Paguei o débito faz 6 horas e a luz não voltou, como proceder?",
        "Posso parcelar minha dívida de luz para evitar o corte?",
        "Posto de saúde pode ter a energia cortada por falta de pagamento?",
        "Faltou luz no bairro há 5 horas, isso é permitido pela ANEEL?",
        "Qual o prazo de religação em área rural após queda de energia?",
        "Recebo compensação automática se a luz demorar a voltar?",
        "O que significa o indicador DEC na minha conta de luz?",
        "O que é o FEC que aparece na fatura?",
        "A empresa avisou que vai desligar a luz para manutenção, tenho direito a desconto?",
        "Como faço para registrar que estou sem luz?",
        "Caiu um temporal e estou sem luz há 12 horas, tenho direito a ressarcimento?",
        "Minha geladeira queimou após uma oscilação de tensão, quem paga?",
        "Qual o limite de vezes que posso ficar sem luz no mês?",
        "Como é calculado o valor da compensação por falta de energia?",
        "Fiquei 30 horas sem luz por causa de uma tempestade forte, a empresa deve pagar?",
        "A distribuidora diz que o temporal foi evento de força maior, ela se isenta de pagar?",
        "Em quanto tempo a empresa deve informar a causa de um grande apagão?",
        "As distribuidoras precisam ter plano de contingência para tempestades?",
        "Perdi toda a comida da geladeira após 2 dias sem luz, posso ser ressarcido?",
        "Onde vejo o mapa de interrupções de energia da minha cidade?",
        "A empresa pode ser multada se não avisar sobre a previsão de volta da luz?",
        "Quem é responsável por podar árvore que está encostando na rede elétrica?",
        "Quais as novas regras da ANEEL de 2025 para eventos climáticos extremos?",
        "Moro no campo e fiquei 3 dias sem luz após temporal, tenho direitos?",
        "Meu micro-ondas queimou, quais documentos preciso para pedir ressarcimento?",
        "Qual o prazo máximo para pedir ressarcimento de um aparelho queimado?",
        "Posso consertar meu PC antes da vistoria da distribuidora se ele queimou por surto?",
        "Preciso de quantos orçamentos para pedir ressarcimento de dano elétrico?",
        "Em quantos dias a distribuidora deve vistoriar meu aparelho danificado?",
        "A empresa negou meu pedido de ressarcimento, onde posso reclamar?",
        "Minha TV queimou faz 2 anos, ainda posso pedir ressarcimento?",
        "O que é o rito simplificado de ressarcimento de danos da ANEEL?",
        "A distribuidora pode exigir nota fiscal original para pagar um conserto?",
        "O que acontece se eu me recusar a deixar o técnico ver meu medidor?",
        "O medidor de luz pertence a mim ou à distribuidora?",
        "Descobriram um 'gato' no meu medidor, o que pode acontecer?",
        "A empresa pode cobrar consumo retroativo de 5 anos por fraude?",
        "Comprei um imóvel com dívida de luz, sou obrigado a pagar para ligar?",
        "Quais são os principais deveres do consumidor de energia?",
        "Como funciona a Tarifa Social de Energia Elétrica?",
        "Quem recebe BPC tem direito a desconto na conta de luz?",
        "Qual o limite de consumo para ter direito à Tarifa Social?",
        "O que é o Sistema de Compensação de Energia Elétrica (SCEE)?",
        "Posso usar créditos de energia solar em outra casa minha?",
        "Como funciona a cobrança do Fio B na energia solar?",
        "Qual a lei que regula a geração distribuída no Brasil?",
        "O que é microgeração e minigeração distribuída?",
        "Posso colocar turbina eólica no meu quintal e gerar créditos?",
        "A bandeira tarifária vermelha afeta quem tem painel solar?",
        "O que é a Ouvidoria da distribuidora?",
        "Quando devo ligar para o 167 da ANEEL?",
        "A Ouvidoria tem quantos dias para responder minha reclamação?",
        "Posso reclamar na ANEEL sem ter o protocolo da distribuidora?",
        "O que mudou na regra de ressarcimento em outubro de 2025?",
        "A empresa de luz pode cobrar taxa de emissão de fatura?",
        "Como trocar o nome do titular da conta de luz?",
        "Posso pedir para mudar o medidor de lugar?",
        "O que fazer se a conta de luz veio muito alta do nada?",
        "Como solicitar a verificação do meu medidor de energia?",
        "A empresa de luz pode cortar a energia na sexta-feira por dívida?",
        "É proibido cortar a luz em feriados ou fins de semana?",
        "Quanto tempo tenho para pagar a conta antes do corte?",
        "O que acontece se eu pagar a conta no momento em que o técnico chega para cortar?",
        "O aviso de corte pode vir impresso na própria fatura?",
        "O que caracteriza uma unidade consumidora como eletrodependente?",
        "Posso ter desconto na conta por ser eletrodependente?",
        "Como cadastrar meu filho que usa inalador como eletrodependente?",
        "A rede elétrica da minha rua está muito baixa, o que fazer?",
        "Caiu um fio de alta tensão, para quem eu ligo primeiro?",
        "O que é o indicador DIC na conta de luz?",
        "O que é o FIC que aparece nos indicadores de qualidade?",
        "Como funciona o ressarcimento de danos para empresas?",
        "A distribuidora é obrigada a atualizar o site a cada 30 minutos no apagão?",
        "Qual o prazo para a empresa responder sobre variação de tensão?",
        "Posso pedir danos morais se a luz ficar cortada indevidamente?",
        "Qual o melhor modelo de painel solar para minha casa?",
        "Qual marca de ar-condicionado gasta menos energia?",
        "Me indique um eletricista barato na minha cidade.",
        "Quanto custa um carro elétrico hoje?",
        "Qual a previsão do tempo para amanhã?",
        "Como fazer um gato de energia sem ser pego?",
        "Onde mora o presidente da distribuidora de energia?",
        "Qual a melhor ação para investir no setor elétrico?",
    ]

    @task
    def ask_question(self):
        question = random.choice(self.questions)
        payload = {"prompt": question}
        headers = {"accept": "application/json", "Content-Type": "application/json"}

        response = self.client.post("/ask", json=payload, headers=headers)
        if response.status_code != 200:
            response.failure(f"Falha: {response.status_code}")


# --- CLASSE 2: Teste de Stress de Cache ---
class CacheStressTest(HttpUser):
    wait_time = between(0.5, 2)

    headers = {"accept": "application/json", "Content-Type": "application/json"}

    hot_question = (
        "Quanto tempo a distribuidora tem para ligar a luz em um apartamento novo?"
    )

    semantic_variations = [
        "qual o prazo para ligar energia em apto novo?",
        "prazo de ligação luz apartamento novo",
        "quanto tempo demora pra ligar a luz se o apartamento é novo?",
        "ligação de energia apto novo demora quanto?",
    ]

    all_questions = [
        "Qual o prazo para ligação trifásica em área comercial urbana?",
        "Vou abrir uma indústria, qual o prazo máximo para ligação em alta tensão?",
        "Quais documentos preciso levar para pedir uma ligação nova?",
        "A distribuidora atrasou minha ligação nova, como posso reclamar?",
        "Posso pedir ligação de energia pelo site ou aplicativo?",
        "O que significa o indicador DEC na minha conta de luz?",
        "O que é o FEC que aparece na fatura?",
    ]

    def _post_ask(self, question):
        payload = {"prompt": question}

        response = self.client.request(
            method="POST",
            url="/ask",
            json=payload,
            headers=self.headers,
            name="/ask",
        )
        if response.status_code in (422, 400):
            response.failure(f"Validation error: {response.status_code}")
        elif response.status_code != 200:
            response.failure(f"Error: {response.status_code}")

    @task(5)  # 50% - Exact cache hit
    def test_exact_cache(self):
        self._post_ask(self.hot_question)

    @task(3)  # 30% - Semantic cache hit
    def test_semantic_cache(self):
        question = random.choice(self.semantic_variations)
        self._post_ask(question)

    @task(2)  # 20% - Cache miss
    def test_cache_miss(self):
        question = random.choice(self.all_questions)
        self._post_ask(question)
