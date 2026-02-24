import os
from typing import List, Any
from asgiref.sync import sync_to_async

# Pydantic AI imports
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

# Your Django Models
from .models import Session, Message, Connection


class AgentWorkflow:
    def __init__(self, session_id: int):
        self.session_id = session_id

    async def run(self, user_input: str) -> Any:
        """
        Main entry point: Loads session, runs agent, saves results.
        """
        # 1. Fetch Session and Django Agent (Async wrapper needed for ORM access)
        session = await Session.objects.select_related(
            "agent__connection", "agent__config"
        ).aget(id=self.session_id)
        django_agent = session.agent

        # 2. Configure the LLM Model based on Connection
        model_instance = self._get_pydantic_model(django_agent.connection)

        # 3. Initialize Pydantic AI Agent
        # We use the 'output_type' property you defined in your model
        agent = PydanticAgent(
            model=model_instance,
            system_prompt=django_agent.system_prompt,
            result_type=django_agent.output_type,
        )

        # 4. Load Message History
        history = await self._get_message_history(session)

        # 5. Run the Agent
        # Note: We pass the config parameters (temp, top_p) if they exist
        run_kwargs = {}
        if django_agent.config:
            # Map Django Config fields to pydantic-ai run settings if supported
            # or model_settings depending on the specific model implementation
            pass

        result = await agent.run(user_input, message_history=history)

        # 6. Persist the Interaction
        await self._save_interaction(session, user_input, result)

        return result.data

    def _get_pydantic_model(self, connection: Connection):
        """
        Maps Django Connection to pydantic-ai Model.
        """
        if not connection:
            # Fallback or raise error
            raise ValueError("No connection defined for this agent.")

        # Example for OpenAI compatible endpoints (works for Ollama, vLLM, etc.)
        if connection.provider in [
            Connection.Provider.OPENAI,
            Connection.Provider.OLLAMA,
        ]:
            return OpenAIModel(
                model_name=connection.model,
                base_url=connection.endpoint,
                api_key=os.getenv(
                    "OPENAI_API_KEY", "missing-key"
                ),  # Handle auth appropriately
            )

        # Add other providers (Anthropic, Google) here as needed
        raise NotImplementedError(f"Provider {connection.provider} not supported yet.")

    async def _get_message_history(self, session: Session) -> List[ModelMessage]:
        """
        Converts Django Messages to pydantic-ai ModelMessages.
        """
        history: List[ModelMessage] = []

        # Async iteration over Django queryset
        async for msg in session.messages.all().order_by("sequence"):
            if msg.role == Message.Role.USER:
                history.append(
                    ModelRequest(parts=[UserPromptPart(content=msg.payload["content"])])
                )
            elif msg.role == Message.Role.ASSISTANT:
                # Assuming payload stores the structured result or text
                # You might need to adjust logic if payload is complex JSON
                content = str(msg.payload)
                history.append(ModelResponse(parts=[TextPart(content=content)]))

        return history

    async def _save_interaction(self, session: Session, user_input: str, result):
        """
        Saves the User input and Agent output to the DB.
        """
        # Calculate next sequence number
        last_msg = await session.messages.order_by("-sequence").afirst()
        next_seq = (last_msg.sequence + 1) if last_msg else 1

        # 1. Save User Message
        await Message.objects.acreate(
            session=session,
            role=Message.Role.USER,
            payload={"content": user_input},
            sequence=next_seq,
        )

        # 2. Save Assistant Message
        # result.data contains the validated Pydantic model defined in output_type
        # We dump it to JSON for storage
        response_payload = result.data.model_dump(mode="json")

        await Message.objects.acreate(
            session=session,
            role=Message.Role.ASSISTANT,
            payload=response_payload,
            sequence=next_seq + 1,
        )
