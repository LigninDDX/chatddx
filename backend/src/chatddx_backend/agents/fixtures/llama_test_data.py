# fixtures/llama_test_data.py
# pyright: reportUnusedCallResult=false

from chatddx_backend.api.models import Tool, Message, MessageSet, LLMConfig


def handle():
    # Create Tools
    tools = [
        Tool.objects.create(
            name="web_search",
            description="Search the web for current information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"],
            },
        ),
        Tool.objects.create(
            name="calculator",
            description="Perform mathematical calculations",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate",
                    }
                },
                "required": ["expression"],
            },
        ),
        Tool.objects.create(
            name="get_weather",
            description="Get current weather for a location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or coordinates",
                    },
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature units",
                    },
                },
                "required": ["location"],
            },
        ),
        Tool.objects.create(
            name="code_interpreter",
            description="Execute Python code in a sandboxed environment",
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute",
                    }
                },
                "required": ["code"],
            },
        ),
    ]

    messages = [
        Message.objects.create(
            role=Message.Role.SYSTEM,
            content="You are a helpful AI assistant powered by Llama. You are knowledgeable, concise, and always strive to provide accurate information.",
        ),
        Message.objects.create(
            role=Message.Role.USER, content="What is the capital of France?"
        ),
        Message.objects.create(
            role=Message.Role.ASSISTANT, content="The capital of France is Paris."
        ),
        Message.objects.create(
            role=Message.Role.USER, content="Can you calculate 15 * 23 + 47?"
        ),
        Message.objects.create(
            role=Message.Role.ASSISTANT,
            content=[
                {
                    "type": "text",
                    "text": "I'll use the calculator tool to compute that for you.",
                },
                {
                    "type": "tool_use",
                    "id": "calc_001",
                    "name": "calculator",
                    "input": {"expression": "15 * 23 + 47"},
                },
            ],
        ),
        Message.objects.create(
            role=Message.Role.TOOL,
            content={"tool_use_id": "calc_001", "result": "392"},
        ),
        Message.objects.create(
            role=Message.Role.ASSISTANT,
            content="The result is 392 (15 × 23 = 345, plus 47 equals 392).",
        ),
        Message.objects.create(
            role=Message.Role.USER,
            content=[
                {"type": "text", "text": "What's in this image?"},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                    },
                },
            ],
        ),
        Message.objects.create(
            role=Message.Role.REASONING,
            content="Let me analyze the mathematical pattern to find the solution step by step.",
        ),
        Message.objects.create(
            role=Message.Role.THOUGHT,
            content="The user is asking about debugging. I should provide practical examples.",
        ),
    ]

    # Configuration 1: Basic Llama chat
    llm_basic = LLMConfig.objects.create(
        name="llama-3-8b-chat",
        provider=LLMConfig.Provider.OPENAI,
        model="llama-3-8b-instruct",
        endpoint="http://localhost:8000/v1",
        api_key="local-llama-key",
        temperature=0.7,
        top_p=0.9,
        top_k=40,
        max_tokens=2048,
        result_schema="",
        stream=False,
        n=1,
        presence_penalty=0.0,
        frequency_penalty=0.0,
    )
    llm_basic.tools.add(tools[0], tools[1])

    MessageSet.objects.create(
        llm_config=llm_basic,
        message=messages[0],  # system
        order=0,
    )
    MessageSet.objects.create(
        llm_config=llm_basic,
        message=messages[1],  # user
        order=1,
    )
    MessageSet.objects.create(
        llm_config=llm_basic,
        message=messages[2],  # assistant
        order=2,
    )

    # Configuration 2: Llama with tools and specific parameters
    llm_tools = LLMConfig.objects.create(
        name="llama-3-70b-tools",
        provider=LLMConfig.Provider.OPENAI,
        model="llama-3-70b-instruct",
        endpoint="http://localhost:8001/v1",
        api_key="local-llama-key-70b",
        temperature=0.3,
        top_p=0.95,
        top_k=50,
        max_tokens=4096,
        result_schema="",
        tool_choice={"type": "auto"},
        stop_sequences=["<|eot_id|>", "<|end_of_text|>"],
        stream=True,
        n=1,
        presence_penalty=0.1,
        frequency_penalty=0.1,
        provider_params={
            "repetition_penalty": 1.1,
            "rope_scaling": {"type": "dynamic", "factor": 2.0},
        },
    )
    llm_tools.tools.set(tools)  # Add all tools

    # Add conversation with tool use
    for i, msg_idx in enumerate([0, 3, 4, 5, 6]):
        MessageSet.objects.create(
            llm_config=llm_tools, message=messages[msg_idx], order=i
        )
    message_set_tools = MessageSet.objects.get(
        llm_config=llm_tools,
        message=messages[4],  # Assistant message with tool use
    )
    message_set_tools.tools.add(tools[1])  # calculator tool

    # Configuration 3: Creative writing config
    llm_creative = LLMConfig.objects.create(
        name="llama-3-creative",
        provider=LLMConfig.Provider.OPENAI,
        model="llama-3-8b-instruct",
        endpoint="http://localhost:8000/v1",
        api_key="local-llama-key",
        temperature=1.2,
        top_p=0.92,
        top_k=100,
        max_tokens=8192,
        result_schema="",
        seed=42,
        stream=False,
        n=3,  # Generate 3 variations
        presence_penalty=0.6,
        frequency_penalty=0.8,
        logit_bias={"13": -5, "1169": 2},  # Example token biases
        provider_params={
            "mirostat_mode": 2,
            "mirostat_tau": 5.0,
            "mirostat_eta": 0.1,
        },
    )

    MessageSet.objects.create(
        llm_config=llm_creative,
        message=Message.objects.create(
            role=Message.Role.SYSTEM,
            content="You are a creative writing assistant. Help users craft compelling stories and narratives.",
        ),
        order=0,
    )

    llm_code = LLMConfig.objects.create(
        name="llama-3-code",
        provider=LLMConfig.Provider.OPENAI,
        model="llama-3-8b-instruct",
        endpoint="http://localhost:8000/v1",
        api_key="local-llama-key",
        temperature=0.2,
        top_p=0.95,
        max_tokens=16384,
        result_schema="",
        stop_sequences=["```\n\n", "# End of code"],
        stream=True,
        provider_params={
            "grammar": "json",
            "min_p": 0.05,
        },
    )
    llm_code.tools.add(tools[3])

    MessageSet.objects.create(
        llm_config=llm_code,
        message=Message.objects.create(
            role=Message.Role.SYSTEM,
            content="You are an expert programmer. Provide clean, well-documented code with explanations.",
        ),
        order=0,
    )
