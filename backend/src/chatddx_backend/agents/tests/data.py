import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from chatddx_backend.agents.models import Agent, Config, Connection, Schema, Tool

current_dir = Path(__file__).parent


@dataclass
class LLModel:
    GEMMA3_4B = "gemma3:4b"
    GEMMA3_12B = "gemma3:12b"
    LLAMA31_8B = "llama3.1:8b"
    MEDLLAMA2_7B = "medllama2:7b"
    MISTRAL_7B = "mistral:7b"
    QWEN3_8B = "Qwen/Qwen3-8B-AWQ"
    QWEN3_14B = "qwen3:14b-q4_K_M"
    DEEPSEEK_8B = "deepseek-r1:8b-llama-distill-q8_0"
    DEEPSEEK_14B = "deepseek-r1:14b-qwen-distill-q4_K_M"


class TestDataSet(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    connections: dict[str, Connection]
    configs: dict[str, Config]
    schemas: dict[str, Schema]
    agents: dict[str, Agent]
    prompts: dict[str, str]
    tools: dict[str, Tool]


def update_set_a():
    with open(current_dir / "type_check.json") as f:
        Schema.objects.filter(name="type_check").update(
            definition=json.load(f),
        )


def create_set_a():

    data = TestDataSet(
        connections={},
        configs={},
        schemas={},
        agents={},
        prompts={},
        tools={},
    )

    data.connections["qwen3_8b"] = Connection.objects.create(
        model=LLModel.QWEN3_8B,
        provider=Connection.Provider.VLLM,
        endpoint="http://pelle.km:12009/v1",
    )

    data.configs["deterministic"] = Config.objects.create(
        name="deterministic",
        temperature=1,
        top_p=1,
        seed=0,
    )

    data.configs["no_thinking"] = Config.objects.create(
        name="no_thinking",
        seed=0,
        provider_params={
            "extra_body": {
                "chat_template_kwargs": {
                    "enable_thinking": False,
                },
            }
        },
    )

    data.schemas["bool"] = Schema.objects.create(
        name="bool",
        definition={"type": "bool"},
    )
    with open(current_dir / "type_check.json") as f:
        data.schemas["type_check"] = Schema.objects.create(
            name="type_check",
            definition=json.load(f),
        )

    with open(current_dir / "ddx_management.json") as f:
        data.schemas["ddx_management"] = Schema.objects.create(
            name="ddx_management",
            definition=json.load(f),
        )

    data.tools["dice"] = Tool.objects.create(
        name="dice",
        type=Tool.ToolType.FUNCTION,
    )

    data.tools["get_player_name"] = Tool.objects.create(
        name="get_player_name",
        type=Tool.ToolType.FUNCTION,
    )

    data.tools["is_prime"] = Tool.objects.create(
        name="is_prime",
        type=Tool.ToolType.FUNCTION,
    )

    data.agents["test_structure_tool"] = Agent.objects.create(
        name="test_structure_tool",
        connection=data.connections["qwen3_8b"],
        validation_strategy=Agent.ValidationStrategy.INFORM,
        coercion_strategy=Agent.CoercionStrategy.TOOL,
        config=data.configs["deterministic"],
        schema=data.schemas["type_check"],
    )

    data.agents["test_structure_prompted"] = Agent.objects.create(
        name="test_structure_prompted",
        connection=data.connections["qwen3_8b"],
        validation_strategy=Agent.ValidationStrategy.INFORM,
        coercion_strategy=Agent.CoercionStrategy.PROMPTED,
        config=data.configs["deterministic"],
        schema=data.schemas["type_check"],
    )

    data.agents["test_structure_native"] = Agent.objects.create(
        name="test_structure_native",
        connection=data.connections["qwen3_8b"],
        validation_strategy=Agent.ValidationStrategy.INFORM,
        coercion_strategy=Agent.CoercionStrategy.NATIVE,
        config=data.configs["deterministic"],
        schema=data.schemas["type_check"],
    )

    data.agents["test_free_text_no_thinking"] = Agent.objects.create(
        name="test_free_text_no_thinking",
        connection=data.connections["qwen3_8b"],
        config=data.configs["no_thinking"],
    )

    data.agents["test_tools"] = Agent.objects.create(
        name="test_tools",
        connection=data.connections["qwen3_8b"],
        config=data.configs["no_thinking"],
        instructions=(
            "You're a dice game, you should roll the die and see if the number "
            "you get back matches the user's guess. If so, tell them they're a winner. "
            "use the get_player_name tool to address the user"
        ),
    )
    data.agents["test_tools"].tools.set(
        [
            data.tools["dice"],
            data.tools["get_player_name"],
        ]
    )

    data.agents["test_tools"] = Agent.objects.prefetch_related(
        "tools",
        "connection",
        "config",
    ).get(pk=data.agents["test_tools"].pk)

    data.agents["test_tools_prime"] = Agent.objects.create(
        name="test_tools_prime",
        connection=data.connections["qwen3_8b"],
        use_tools=True,
        config=data.configs["no_thinking"],
        instructions=("use the is_prime tool to determine if user's number is a prime"),
        schema=data.schemas["bool"],
    )
    data.agents["test_tools_prime"].tools.set(
        [
            data.tools["is_prime"],
        ]
    )

    data.agents["test_tools_prime"] = Agent.objects.prefetch_related(
        "tools",
        "connection",
        "config",
        "schema",
    ).get(pk=data.agents["test_tools_prime"].pk)

    data.agents["ddx_management"] = Agent.objects.create(
        name="ddx_management",
        connection=data.connections["qwen3_8b"],
        use_tools=True,
        schema=data.schemas["ddx_management"],
    )

    data.prompts["case_a"] = (
        "A previously healthy 60-year-old man comes to his physician because of progressively worsening shortness of breath for the past 2 months. He does not experience shortness of breath at rest. He also occasionally has a dry cough. He has not had fever, chills, or night sweats. He has smoked a pack of cigarettes daily for the past 40 years. He drinks a beer daily and occasionally more on weekends. He does not use illicit drugs. He is 183 cm (6 ft 0 in) tall and weighs 66 kg (145 lbs); BMI is 19.7 kg/m2. His temperature is 37 °C (98.6 °F), pulse is 94/min, respirations are 21/min, and blood pressure is 136/88 mm Hg. Lung auscultation reveals a prolonged expiratory phase and end-expiratory wheezing. Spirometry shows an FEV1:FVC ratio of 62%, an FEV1 of 60% of predicted, and a total lung capacity of 125% of predicted. The diffusion capacity of the lung (DLCO) is decreased."
    )

    return data


def test_result_ddx_3(self):
    # i = "A previously healthy 60-year-old man comes to his physician because of progressively worsening shortness of breath for the past 2 months. He does not experience shortness of breath at rest. He also occasionally has a dry cough. He has not had fever, chills, or night sweats. He has smoked a pack of cigarettes daily for the past 40 years. He drinks a beer daily and occasionally more on weekends. He does not use illicit drugs. He is 183 cm (6 ft 0 in) tall and weighs 66 kg (145 lbs); BMI is 19.7 kg/m2. His temperature is 37 °C (98.6 °F), pulse is 94/min, respirations are 21/min, and blood pressure is 136/88 mm Hg. Lung auscultation reveals a prolonged expiratory phase and end-expiratory wheezing. Spirometry shows an FEV1:FVC ratio of 62%, an FEV1 of 60% of predicted, and a total lung capacity of 125% of predicted. The diffusion capacity of the lung (DLCO) is decreased."

    data = {
        "disposition": [
            "Follow-up with pulmonology for COPD management",
            "Referral to smoking cessation program",
        ],
        "empiric_therapy": [
            "Smoking cessation counseling",
            "Short-acting bronchodilator (e.g., albuterol) for symptomatic relief",
            "Pulmonary rehabilitation referral",
        ],
        "possible_diagnoses": [
            {
                "clinical_rationale": "Chronic obstructive pulmonary disease (COPD) due to long-term smoking, obstructive pattern on spirometry (FEV1/FVC 62%), decreased DLCO, and symptoms of progressive dyspnea with prolonged expiration.",
                "diagnosis": "Chronic Obstructive Pulmonary Disease (COPD)",
                "key_negatives": "No acute features (e.g., fever, purulent sputum), no history of occupational exposures suggesting interstitial lung disease",
                "likelyhood": "High",
                "urgency": "Stable",
            }
        ],
        "warnings": [
            "Longstanding smoking history increases risk of COPD exacerbations and lung cancer"
        ],
        "workup": [
            {
                "priority": "Routine",
                "test_name": "Repeat spirometry with bronchodilation test to confirm obstructive pattern and assess reversibility",
            },
            {
                "priority": "Routine",
                "test_name": "Chest X-ray to rule out alternative diagnoses (e.g., lung cancer, interstitial disease)",
            },
            {
                "priority": "Routine",
                "test_name": "Diffusion capacity (DLCO) testing to evaluate for emphysema",
            },
        ],
    }


def result_ddx_2():
    i = "A previously healthy 60-year-old man comes to his physician because of progressively worsening shortness of breath for the past 2 months. He does not experience shortness of breath at rest. He also occasionally has a dry cough. He has not had fever, chills, or night sweats. He has smoked a pack of cigarettes daily for the past 40 years. He drinks a beer daily and occasionally more on weekends. He does not use illicit drugs. He is 183 cm (6 ft 0 in) tall and weighs 66 kg (145 lbs); BMI is 19.7 kg/m2. His temperature is 37 °C (98.6 °F), pulse is 94/min, respirations are 21/min, and blood pressure is 136/88 mm Hg. Lung auscultation reveals a prolonged expiratory phase and end-expiratory wheezing. Spirometry shows an FEV1:FVC ratio of 62%, an FEV1 of 60% of predicted, and a total lung capacity of 125% of predicted. The diffusion capacity of the lung (DLCO) is decreased."

    o = {
        "possible_diagnoses": [
            {
                "diagnosis": "Chronic Obstructive Pulmonary Disease (COPD) - Emphysema",
                "clinical_rationale": "Progressive dyspnea, smoking history, obstructive spirometry (FEV1/FVC 62%), reduced DLCO, and elevated TLC are consistent with COPD, specifically emphysema.",
                "key_negatives": None,
                "urgency": "Stable",
                "likelyhood": "High",
            }
        ],
        "workup": [
            {
                "test_name": "Chest X-ray (to evaluate for hyperinflation, bullae, or alternative diagnoses)",
                "priority": "Routine",
            },
            {
                "test_name": "Arterial Blood Gas (ABG) if hypoxemia is suspected",
                "priority": "Routine",
            },
        ],
        "warnings": [
            "High risk of exacerbations due to advanced disease and continued smoking",
            "Potential for progressive lung function decline",
        ],
        "empiric_therapy": [
            "Smoking cessation counseling and referrals",
            "Long-acting beta-agonist (LABA) + long-acting muscarinic antagonist (LAMA) combination therapy (e.g., aclidinium + formoterol)",
            "Inhaled corticosteroids if frequent exacerbations (e.g., fluticasone 100-500 mcg bid)",
        ],
        "disposition": [
            "Follow-up with pulmonology for COPD management",
            "Referral to smoking cessation programs",
        ],
    }


def result_ddx_1():
    i = "A 46-year-old woman comes to the physician because of a 3-day history of diarrhea, moderate abdominal pain, and weakness. Her symptoms began on the return flight from a 2-week yoga retreat in India, where she stayed at a resort. She was mildly nauseous as she boarded the flight, and diarrhea followed immediately after eating the in-flight meal. Since then, she has had up to five watery stools daily. She has a 1-year history of gastroesophageal reflux disease and is allergic to shellfish. Her only medication is ranitidine. She appears lethargic. Her temperature is 37 °C (98.6 °F), pulse is 70/min, and blood pressure is 115/72 mm Hg. Abdominal examination shows diffuse tenderness with no guarding or rebound. Bowel sounds are hyperactive."

    o = {
        "possible_diagnoses": [
            {
                "diagnosis": "Traveler's Diarrhea",
                "clinical_rationale": "Recent travel to India, onset after in-flight meal, watery diarrhea, and abdominal pain are classic for bacterial enteropathogens (e.g., E. coli, Shigella) acquired during travel.",
                "key_negatives": None,
                "urgency": "Stable",
                "likelyhood": "High",
            },
            {
                "diagnosis": "Giardiasis",
                "clinical_rationale": "Exposure to contaminated water during her stay in India, with watery diarrhea and abdominal pain; however, typically presents with more prolonged symptoms (>2 weeks).",
                "key_negatives": None,
                "urgency": "Stable",
                "likelyhood": "Moderate",
            },
            {
                "diagnosis": "Viral Gastroenteritis",
                "clinical_rationale": "Acute diarrhea following travel",
                "key_negatives": "Geographic context and absence of viral symptoms (no fever)",
                "urgency": "Stable",
                "likelyhood": "Low",
            },
        ],
        "workup": [
            {
                "test_name": "Stool Studies (Ova and Parasites, Culture, PCR for pathogens)",
                "priority": "STAT",
            },
            {
                "test_name": "Complete Blood Count (CBC) and Electrolytes",
                "priority": "Expedited",
            },
            {"test_name": "Basic Metabolic Panel (BMP)", "priority": "Expedited"},
        ],
        "warnings": [
            "Lethargy suggesting possible dehydration",
            "Risk of electrolyte imbalance from profuse diarrhea",
        ],
        "empiric_therapy": [
            "Oral rehydration solution (e.g., WHO formulation)",
            "Azithromycin 500 mg PO once daily for 3 days if symptoms severe or not improving (consider due to high-risk travel location)",
        ],
        "disposition": [
            "Outpatient with follow-up in 48 hours if symptoms persist or worsen",
            "Admit to hospital if signs of severe dehydration or hemodynamic instability develop",
        ],
    }
