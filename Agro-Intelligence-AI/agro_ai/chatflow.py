"""Uma rota funcional compartilhada pelo Streamlit e pela avaliação."""
from agro_ai.agents.orchestrator import AgentOrchestrator,plan_agents
from agro_ai.ml.inference import ml_chat_response,is_prediction_request,parse_features,MLInputError
from agro_ai.observability import observation


class ChatTurn:
    def __init__(self,settings,gateway_factory,index_factory):
        self.settings=settings
        self.gateway_factory=gateway_factory
        self.index_factory=index_factory
        self.orchestrator=None
        self.prepared=None
        self.local_answer=None
        self.sources=[]
        self.tools=[]
        self.evidence={}
        self.answer_mode='unknown'

    def prepare(self,history):
        self.history=history
        prompt=history[-1]['content']
        if is_prediction_request(prompt) and plan_agents(prompt)!=['estoque','comercial']:
            captured=[]
            with observation('orchestration.ml_local',as_type='chain'):
                with observation('agent.estoque',as_type='agent',agent='estoque'):
                    with observation('ml.local_response',as_type='tool',tool='ml_local'):
                        self.local_answer=ml_chat_response(prompt,on_result=captured.append)
            status='ok' if captured else 'needs_input'
            if not captured:
                try:
                    parse_features(prompt)
                    status='failed'
                except MLInputError:
                    pass
            self.tools=[{'agent':'estoque','tool':'validacao_e_inferencia_ml_local','status':status}]
            self.evidence={'ml':captured[0]} if captured else {}
            self.answer_mode='ml_local'
        else:
            self.orchestrator=AgentOrchestrator(self.settings,self.gateway_factory,self.index_factory)
            self.prepared=self.orchestrator.prepare(history)
            self.sources=self.prepared.state.sources
            self.tools=self.prepared.state.trace
            self.evidence=self.prepared.state.results
        return self

    def stream(self):
        if self.local_answer is not None:
            yield self.local_answer
        else:
            yield from self.orchestrator.stream_answer(self.prepared,self.history)
            self.answer_mode=self.prepared.state.answer_mode

    def close(self):
        if self.orchestrator:
            self.orchestrator.close()
