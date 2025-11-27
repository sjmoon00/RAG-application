from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, FewShotChatMessagePromptTemplate
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

from langchain_upstage import UpstageEmbeddings
from langchain_upstage import ChatUpstage

from langchain_chroma import Chroma


from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from config import answer_examples

store = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


def get_retriever():
    embedding = UpstageEmbeddings(model='solar-embedding-1-large')
    database = Chroma(collection_name='chroma-tax', persist_directory="../chroma", embedding_function=embedding)
    retriever = database.as_retriever(search_kwargs={'k': 4})
    return retriever


def get_history_retriever():
    llm = get_llm()
    retriever = get_retriever()
    
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )

    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )
    return history_aware_retriever


def get_llm(model='solar-pro2'):
    llm = ChatUpstage(model=model)
    return llm


def get_dictionary_chain():
    dictionary = ["사람을 나타내는 표현 -> 거주자"]
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(f"""
        사용자의 질문을 보고, 우리의 사전을 참고해서 사용자의 질문을 변경해주세요.
        만약 변경할 필요가 없다고 판단된다면, 사용자의 질문을 변경하지 않아도 됩니다.
        그런 경우에는 질문만 리턴해주세요
        사전: {dictionary}
        
        질문: {{question}}
    """)

    dictionary_chain = prompt | llm | StrOutputParser()
    
    return dictionary_chain


def get_rag_chain():
    llm = get_llm()
    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{input}"),
            ("ai", "{answer}"),
        ]
    )
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=answer_examples,
    )
    system_prompt = (
        "당신은 대한민국 소득세법 전문가 챗봇입니다. 아래 지침을 엄격히 준수하여 답변하세요.\n\n"
        
        "사용자는 주로 '세금'이라고 말할 때, '4대보험을 포함한 모든 공제금액'을 궁금해합니다.\n"
        "따라서 계산 질문에는 반드시 **4대보험료**와 **소득세**를 구분하여 계산하고 합산해 주어야 합니다.\n\n"

        "### 1. 답변 원칙\n"
        "- 제공된 문맥(Context)을 기반으로 정확한 법적 근거를 제시하세요.\n"
        "- 근거가 되는 법률 조항은 반드시 **[소득세법 제XX조]** 형식으로 명시하세요.\n"
        "- 문맥에서 답을 찾을 수 없다면 솔직하게 모른다고 답하세요.\n\n"

        "### 2. 필수 참고 조항 (우선 순위)\n"
        "답변 시 아래 조항들이 포함된 문맥을 최우선으로 검토하세요:\n"
        "- 제47조 (근로소득공제)\n"
        "- 제50조 (기본공제)\n"
        "- 제51조의3 (연금보험료공제)\n"
        "- 제52조 (특별소득공제)\n"
        "- 제55조 (세율)\n"
        "- 제59조 (근로소득세액공제)\n\n"

        "### 3. 답변 형식\n"
        "- **일반적인 법률 질문:** 핵심 내용을 요약하여 3~5문장 내외로 명확히 설명하세요.\n"
        "- **세금 계산 요청 (예: 연봉 X원의 세금은?):** 반드시 아래의 **'5단계 표준 계산 절차'**를 따르고, 각 단계별 계산식과 법적 근거를 상세히 작성하세요.\n"
        "  1단계: 근로소득금액 계산 (총급여 - 근로소득공제)\n"
        "  2단계: 과세표준 계산 (근로소득금액 - 각종 소득공제)\n"
        "  3단계: 산출세액 계산 (과세표준 × 세율)\n"
        "  4단계: 결정세액 계산 (산출세액 - 세액공제)\n"
        "  5단계: 지방소득세 포함 최종 납부세액\n\n"

        "--- 제공된 문맥(Context) ---\n"
        "{context}"
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            few_shot_prompt,
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = get_history_retriever()
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    ).pick('answer')
    
    return conversational_rag_chain


def get_ai_response(user_message):
    dictionary_chain = get_dictionary_chain()
    rag_chain = get_rag_chain()
    tax_chain = {"input": dictionary_chain} | rag_chain
    ai_response = tax_chain.stream(
        {
            "question": user_message
        },
        config={
            "configurable": {"session_id": "abc123"}
        },
    )

    return ai_response